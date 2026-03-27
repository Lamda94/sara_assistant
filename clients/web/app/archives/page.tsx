"use client";
import { Archive } from "lucide-react";
import Sidebar from "@/components/Sidebar";

export default function ArchivesPage() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 items-center justify-center" style={{ background: "#1A1C1E" }}>
        <Archive size={32} strokeWidth={1.3} style={{ color: "#263238" }} />
        <p className="text-[13px] mt-4" style={{ color: "#455A64" }}>No hay conversaciones archivadas</p>
        <p className="text-[11px] mt-1" style={{ color: "#37474F" }}>Las sesiones pasadas aparecerán aquí</p>
      </div>
    </div>
  );
}
