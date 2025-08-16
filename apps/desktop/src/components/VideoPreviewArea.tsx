import React, { useMemo } from "react";
import { useRealtimeStore } from "../hooks/useRealtimeStore";

const VideoPreviewArea: React.FC = () => {
  // Get the selected file from the store
  const selectedFile = useRealtimeStore((s) => s.selectedFile);
  
  // If no file is selected, try to find the latest video or image
  const fallbackFile = useRealtimeStore((s) => {
    return [...s.projectFiles].reverse().find(
      (f) =>
        (f.type && (f.type === "video" || f.type === "image")) ||
        (f.path && (f.path.toLowerCase().includes(".mp4") || f.path.toLowerCase().includes(".jpg") || f.path.toLowerCase().includes(".png")))
    );
  });

  const mediaFile = selectedFile || fallbackFile;

  const mediaUrl = useMemo(() => {
    if (!mediaFile) return "";
    
    // If we have a direct URL, use it
    if (mediaFile.url) return mediaFile.url;
    
    // If we have a path, try to create a URL
    if (mediaFile.path) {
      // Extract filename from path
      const filename = mediaFile.path.split('/').pop() || mediaFile.path.split('\\').pop() || '';
      
      // Try to extract project ID from the file path
      let projectId = 'default';
      if (mediaFile.path.includes('Projects/')) {
        const projectsMatch = mediaFile.path.match(/Projects\/([^\/\\]+)/);
        if (projectsMatch) {
          projectId = projectsMatch[1];
        }
      }
      
      // Use the general files endpoint that handles all file types
      return `http://127.0.0.1:8001/api/projects/${projectId}/files/${encodeURIComponent(filename)}`;
    }
    
    return "";
  }, [mediaFile]);

  const isVideo = mediaFile?.type === "video" || 
                  (mediaFile?.path && mediaFile.path.toLowerCase().includes(".mp4"));

  if (!mediaFile || !mediaUrl) {
    return (
      <div style={{ padding: 16, color: "#888", textAlign: "center" }}>
        <div style={{ fontSize: 14, marginBottom: 8 }}>Media Preview</div>
        <div style={{ fontSize: 12 }}>No media selected. Click on a file in the Project Files tab to preview it.</div>
      </div>
    );
  }

  return (
    <div style={{ padding: 16 }}>
      <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 8 }}>
        {isVideo ? "Video Preview" : "Image Preview"}
      </div>
      
      {isVideo ? (
        <video
          src={mediaUrl}
          controls
          style={{ width: "100%", maxWidth: 600, borderRadius: 8, background: "#000" }}
          onError={(e) => {
            console.error("Video loading error:", e);
          }}
        />
      ) : (
        <img
          src={mediaUrl}
          alt={mediaFile.name || mediaFile.filename || "Preview"}
          style={{ 
            width: "100%", 
            maxWidth: 600, 
            borderRadius: 8, 
            background: "#000",
            objectFit: "contain"
          }}
          onError={(e) => {
            console.error("Image loading error:", e);
          }}
        />
      )}
      
      <div style={{ fontSize: 12, color: "#aaa", marginTop: 4 }}>
        {mediaFile.name || mediaFile.filename}
      </div>
      {mediaFile.size && (
        <div style={{ fontSize: 12 }}>
          Size: {Math.round(mediaFile.size / 1024)} KB
        </div>
      )}
      {mediaFile.timestamp && (
        <div style={{ fontSize: 12 }}>
          Created: {new Date(mediaFile.timestamp).toLocaleString()}
        </div>
      )}
      <div style={{ fontSize: 12, color: "#666" }}>
        Type: {mediaFile.type || (isVideo ? "video" : "image")}
      </div>
    </div>
  );
};

export default VideoPreviewArea; 