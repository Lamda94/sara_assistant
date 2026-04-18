import express from 'express';
import cors from 'cors';
import { execSync, spawn } from 'child_process';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { resolve } from 'path';

const app = express();
const PORT = 4000;
const CAREER_OPS = '/career-ops';

app.use(cors());
app.use(express.json({ limit: '5mb' }));

// ── Helpers ─────────────────────────────────────────────────────────

function readFileOrNull(path) {
  try {
    return existsSync(path) ? readFileSync(path, 'utf-8') : null;
  } catch {
    return null;
  }
}

async function groqChat(systemPrompt, userMessage) {
  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) throw new Error('GROQ_API_KEY not set');

  const model = process.env.GROQ_MODEL || 'llama-3.3-70b-versatile';

  const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userMessage },
      ],
      temperature: 0.3,
      max_tokens: 4096,
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Groq API ${res.status}: ${text}`);
  }

  const data = await res.json();
  return data.choices?.[0]?.message?.content ?? '';
}

function buildSystemPrompt(modeFile) {
  const shared = readFileOrNull(resolve(CAREER_OPS, 'modes/_shared.md')) || '';
  const mode = readFileOrNull(resolve(CAREER_OPS, modeFile)) || '';
  const cv = readFileOrNull(resolve(CAREER_OPS, 'cv.md')) || '';
  const profile = readFileOrNull(resolve(CAREER_OPS, 'config/profile.yml')) || '';

  let prompt = shared;
  if (mode) prompt += '\n\n' + mode;
  if (cv) prompt += '\n\n## CV\n' + cv;
  if (profile) prompt += '\n\n## Profile\n' + profile;
  return prompt;
}

async function fetchUrlContent(url) {
  try {
    const res = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0 (compatible; career-api/1.0)' },
    });
    return await res.text();
  } catch (err) {
    throw new Error(`Failed to fetch URL: ${err.message}`);
  }
}

// ── POST /scan ──────────────────────────────────────────────────────

app.post('/scan', (req, res) => {
  try {
    const { company } = req.body || {};
    const args = company ? `--company "${company}"` : '';
    const cmd = `node ${resolve(CAREER_OPS, 'scan.mjs')} ${args}`;

    const output = execSync(cmd, {
      cwd: CAREER_OPS,
      encoding: 'utf-8',
      timeout: 120_000,
    });

    // Parse scan output — scan.mjs prints summary lines
    const lines = output.trim().split('\n');
    const offers = [];
    for (const line of lines) {
      // Scan outputs lines like: "  [NEW] Title | Company | Location | URL"
      const match = line.match(/\[NEW\]\s+(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(\S+)/);
      if (match) {
        offers.push({
          title: match[1].trim(),
          company: match[2].trim(),
          location: match[3].trim(),
          url: match[4].trim(),
        });
      }
    }

    res.json({ found: offers.length, offers, raw_output: output });
  } catch (err) {
    res.status(500).json({ error: err.message, stderr: err.stderr?.toString() });
  }
});

// ── POST /evaluate ──────────────────────────────────────────────────

app.post('/evaluate', async (req, res) => {
  try {
    const { url, jd_text } = req.body || {};
    if (!url && !jd_text) {
      return res.status(400).json({ error: 'Provide url or jd_text' });
    }

    let jd = jd_text || '';
    if (url && !jd) {
      jd = await fetchUrlContent(url);
    }

    const systemPrompt = buildSystemPrompt('modes/oferta.md');
    const userMsg = url
      ? `Evaluate this offer:\n\nURL: ${url}\n\n${jd}`
      : `Evaluate this offer:\n\n${jd}`;

    const raw = await groqChat(systemPrompt, userMsg);

    // Parse structured fields from the LLM response
    const scoreMatch = raw.match(/(?:score|puntuaci[oó]n|nota)[:\s]*(\d+(?:\.\d+)?)\s*\/\s*5/i);
    const archetypeMatch = raw.match(/(?:archetype|arquetipo)[:\s]*(.+)/i);
    const compatMatch = raw.match(/(\d+(?:\.\d+)?)\s*%/);
    const legitimacyMatch = raw.match(/(?:legitimacy|legitimidad)[:\s]*(.+)/i);

    const blocks = {};
    for (const letter of ['A', 'B', 'C', 'D', 'E', 'F', 'G']) {
      const blockRe = new RegExp(`##\\s*(?:Block\\s+)?${letter}[\\s.:—-]+(.+?)(?=##\\s*(?:Block\\s+)?[A-G]|$)`, 'is');
      const m = raw.match(blockRe);
      if (m) blocks[letter] = m[1].trim();
    }

    res.json({
      score: scoreMatch ? parseFloat(scoreMatch[1]) : null,
      archetype: archetypeMatch ? archetypeMatch[1].trim() : null,
      compatibility_pct: compatMatch ? parseFloat(compatMatch[1]) : null,
      blocks,
      summary: raw.slice(0, 500),
      legitimacy: legitimacyMatch ? legitimacyMatch[1].trim() : null,
      raw_response: raw,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── POST /generate-cv ───────────────────────────────────────────────

app.post('/generate-cv', (req, res) => {
  try {
    const { html, filename } = req.body || {};
    if (!html) return res.status(400).json({ error: 'Provide html' });

    const outName = filename || 'output.pdf';
    const tmpHtml = resolve(CAREER_OPS, 'output', '_tmp_cv.html');
    const outPath = resolve(CAREER_OPS, 'output', outName);

    mkdirSync(resolve(CAREER_OPS, 'output'), { recursive: true });
    writeFileSync(tmpHtml, html, 'utf-8');

    const cmd = `node ${resolve(CAREER_OPS, 'generate-pdf.mjs')} "${tmpHtml}" "${outPath}"`;
    execSync(cmd, { cwd: CAREER_OPS, encoding: 'utf-8', timeout: 60_000 });

    res.json({ path: `/career-ops/output/${outName}`, success: true });
  } catch (err) {
    res.status(500).json({ error: err.message, success: false });
  }
});

// ── POST /interview-prep ────────────────────────────────────────────

app.post('/interview-prep', async (req, res) => {
  try {
    const { company, role } = req.body || {};
    if (!company || !role) {
      return res.status(400).json({ error: 'Provide company and role' });
    }

    const systemPrompt = buildSystemPrompt('modes/interview-prep.md');
    const userMsg = `Prepare interview prep for the role "${role}" at "${company}".`;

    const prep_text = await groqChat(systemPrompt, userMsg);

    res.json({ company, role, prep_text });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── POST /deep-research ─────────────────────────────────────────────

app.post('/deep-research', async (req, res) => {
  try {
    const { company } = req.body || {};
    if (!company) return res.status(400).json({ error: 'Provide company' });

    const systemPrompt = buildSystemPrompt('modes/deep.md');
    const userMsg = `Deep research on company: "${company}".`;

    const research_text = await groqChat(systemPrompt, userMsg);

    res.json({ company, research_text });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── GET /status ─────────────────────────────────────────────────────

app.get('/status', (_req, res) => {
  try {
    const version = readFileOrNull(resolve(CAREER_OPS, 'VERSION'))?.trim() || 'unknown';

    res.json({
      healthy: true,
      career_ops_version: version,
      files: {
        cv: existsSync(resolve(CAREER_OPS, 'cv.md')),
        profile: existsSync(resolve(CAREER_OPS, 'config/profile.yml')),
        portals: existsSync(resolve(CAREER_OPS, 'portals.yml')),
      },
    });
  } catch (err) {
    res.status(500).json({ healthy: false, error: err.message });
  }
});

// ── POST /configure ─────────────────────────────────────────────────

app.post('/configure', (req, res) => {
  try {
    const { cv_markdown, profile, portals } = req.body || {};

    if (cv_markdown) {
      writeFileSync(resolve(CAREER_OPS, 'cv.md'), cv_markdown, 'utf-8');
    }
    if (profile) {
      mkdirSync(resolve(CAREER_OPS, 'config'), { recursive: true });
      writeFileSync(resolve(CAREER_OPS, 'config/profile.yml'), profile, 'utf-8');
    }
    if (portals) {
      writeFileSync(resolve(CAREER_OPS, 'portals.yml'), portals, 'utf-8');
    }

    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// ── Start ───────────────────────────────────────────────────────────

app.listen(PORT, '0.0.0.0', () => {
  console.log(`career-api listening on 0.0.0.0:${PORT}`);
});
