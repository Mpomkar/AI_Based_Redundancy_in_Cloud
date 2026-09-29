/** Client-side upload guards — server still validates; this gives instant feedback. */

const ALLOWED_EXT = new Set([
  ".pdf",
  ".docx",
  ".jpg",
  ".jpeg",
  ".png",
  ".webp",
  ".gif",
]);

const ZIP_EXT = new Set([".zip", ".rar", ".7z", ".tar", ".gz", ".tgz"]);

export const UPLOAD_HINT =
  "Allowed: PDF, Word (.docx), JPEG, PNG, WebP, GIF. Archives (ZIP) and other types are rejected.";

function extensionOf(name: string): string {
  const i = name.lastIndexOf(".");
  return i >= 0 ? name.slice(i).toLowerCase() : "";
}

/** Returns an error message if the file should not be uploaded, else null. */
export function validateUploadFileClient(file: File): string | null {
  if (!file || file.size <= 0) {
    return "Empty file. Please choose a non-empty PDF, Word (.docx), or image.";
  }
  const ext = extensionOf(file.name || "");
  const mime = (file.type || "").toLowerCase();

  if (
    ext === ".zip" ||
    ZIP_EXT.has(ext) ||
    mime === "application/zip" ||
    mime === "application/x-zip-compressed" ||
    mime.includes("zip")
  ) {
    return "ZIP and other archive files are not supported. Upload PDF, Word (.docx), or an image.";
  }

  if (ext && !ALLOWED_EXT.has(ext)) {
    return "Unsupported file type. Upload PDF, Word (.docx), or image (JPEG, PNG, WebP, GIF).";
  }

  // No extension: allow only known image/pdf MIME (browser may omit name)
  if (!ext) {
    const okMime =
      mime === "application/pdf" ||
      mime ===
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
      mime.startsWith("image/jpeg") ||
      mime.startsWith("image/png") ||
      mime.startsWith("image/webp") ||
      mime.startsWith("image/gif");
    if (!okMime) {
      return "Unsupported file type. Upload PDF, Word (.docx), or image (JPEG, PNG, WebP, GIF).";
    }
  }

  return null;
}

export function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}
