import React from "react";

interface FilePreviewProps {
  type: string;
  url: string;
  name: string;
  path?: string;  // Fallback to path if url is not available
}

const FilePreview: React.FC<FilePreviewProps> = ({ type, url, name, path }) => {
  // Use URL if available, otherwise fall back to path
  const displayUrl = url || path || '';
  
  if (type.startsWith("image")) {
    return <img src={displayUrl} alt={name} style={{ maxWidth: 200, maxHeight: 200, objectFit: 'cover' }} />;
  }
  if (type.startsWith("video")) {
    return <video src={displayUrl} controls style={{ maxWidth: 300 }} />;
  }
  if (type.startsWith("audio")) {
    return <audio src={displayUrl} controls />;
  }
  return <div style={{ fontSize: 12, color: "#888" }}>Cannot preview this file type.</div>;
};

export default FilePreview; 