import React from "react";
import { useRealtimeStore } from "../hooks/useRealtimeStore";
import FilePreview from "./FilePreview";

const ProjectFilesTab: React.FC = () => {
  const files = useRealtimeStore((s) => s.projectFiles);
  const selectedFile = useRealtimeStore((s) => s.selectedFile);
  const selectFile = useRealtimeStore((s) => s.selectFile);

  if (!files || files.length === 0) {
    return <div style={{ padding: 16, color: "#888" }}>No project files yet.</div>;
  }

  const handleFileClick = (file: any) => {
    selectFile(file);
  };

  return (
    <div style={{ padding: 16 }}>
      <h3>Project Files</h3>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 16 }}>
        {files.map((file, idx) => {
          const isSelected = selectedFile?.id === file.id;
          
          return (
            <div 
              key={file.id || file.path || idx} 
              style={{ 
                border: isSelected ? "2px solid #4f8cff" : "1px solid #333", 
                borderRadius: 6, 
                padding: 8, 
                width: 220,
                cursor: "pointer",
                backgroundColor: isSelected ? "rgba(79, 140, 255, 0.1)" : "transparent",
                transition: "all 0.2s ease"
              }}
              onClick={() => handleFileClick(file)}
              onMouseEnter={(e) => {
                if (!isSelected) {
                  e.currentTarget.style.borderColor = "#4f8cff";
                  e.currentTarget.style.backgroundColor = "rgba(79, 140, 255, 0.05)";
                }
              }}
              onMouseLeave={(e) => {
                if (!isSelected) {
                  e.currentTarget.style.borderColor = "#333";
                  e.currentTarget.style.backgroundColor = "transparent";
                }
              }}
            >
              <FilePreview 
                type={file.type || "unknown"} 
                url={file.url || file.path || ""} 
                path={file.path || ""}
                name={file.name || file.filename || ""} 
              />
              <div style={{ fontWeight: 500, marginTop: 8 }}>{file.name || file.filename}</div>
              <div style={{ fontSize: 12, color: "#aaa" }}>Type: {file.type || "unknown"}</div>
              {file.size && <div style={{ fontSize: 12 }}>Size: {Math.round(file.size / 1024)} KB</div>}
              {file.timestamp && <div style={{ fontSize: 12 }}>Created: {new Date(file.timestamp).toLocaleString()}</div>}
              {isSelected && (
                <div style={{ fontSize: 12, color: "#4f8cff", fontWeight: 500, marginTop: 4 }}>
                  ✓ Selected
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ProjectFilesTab; 