"use client";

import { useMemo, useRef, useState } from "react";
import { Paperclip, UploadCloud, X } from "lucide-react";

type FileDropzoneProps = {
  files: File[];
  onChange: (files: File[]) => void;
  label: string;
  helpText?: string;
};

function formatFileSize(bytes: number) {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export function FileDropzone({
  files,
  onChange,
  label,
  helpText = "Drag files here or browse. Images, PDF, and text supported up to 5MB each.",
}: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isOver, setIsOver] = useState(false);

  const previewFiles = useMemo(
    () =>
      files.map((file, index) => ({
        id: `${file.name}-${file.size}-${index}`,
        file,
      })),
    [files],
  );

  const addFiles = (incoming: FileList | File[]) => {
    const next = [...files];
    for (const file of Array.from(incoming)) {
      next.push(file);
    }
    onChange(next);
  };

  return (
    <div className="space-y-3">
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setIsOver(true);
        }}
        onDragLeave={() => setIsOver(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsOver(false);
          addFiles(event.dataTransfer.files);
        }}
        className={`rounded-2xl border border-dashed px-4 py-5 transition ${
          isOver
            ? "border-amber-400/50 bg-amber-500/10"
            : "border-zinc-700/70 bg-zinc-950/50 hover:border-zinc-500/80 hover:bg-zinc-900/60"
        }`}
      >
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/6 bg-black/30 text-amber-300">
            <UploadCloud className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold text-white">{label}</div>
            <p className="mt-1 text-sm leading-6 text-zinc-400">{helpText}</p>
            <div className="mt-3 inline-flex items-center gap-2 rounded-full border border-zinc-700/80 bg-black/30 px-3 py-1.5 text-xs text-zinc-300">
              <Paperclip className="h-3.5 w-3.5" />
              Browse files
            </div>
          </div>
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          accept="image/*,.pdf,.txt"
          onChange={(event) => {
            if (event.target.files?.length) {
              addFiles(event.target.files);
            }
            event.target.value = "";
          }}
        />
      </div>

      {previewFiles.length ? (
        <div className="grid gap-2">
          {previewFiles.map(({ id, file }, index) => (
            <div
              key={id}
              className="flex items-center justify-between gap-3 rounded-2xl border border-zinc-800 bg-zinc-950/60 px-4 py-3"
            >
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-zinc-100">{file.name}</div>
                <div className="mt-1 text-xs text-zinc-500">{formatFileSize(file.size)}</div>
              </div>
              <button
                type="button"
                onClick={() => onChange(files.filter((_, fileIndex) => fileIndex !== index))}
                className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-zinc-700 bg-black/30 text-zinc-400 transition hover:border-rose-400/40 hover:text-rose-200"
                aria-label={`Remove ${file.name}`}
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
