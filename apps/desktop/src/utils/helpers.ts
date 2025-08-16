// Utility helpers for Sclip frontend

export function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleString();
}

// TODO: Add more helpers as needed 