# Sclip Design Guidelines

## Core Design Principles

### 1. Agentic, Autonomous Orchestration
- **AI-First Workflow:** The AI agent (Gemini 2.5 Pro) manages the entire video creation process
- **Deterministic Tools:** All actual work is done by non-AI, deterministic functions
- **Transparent Execution:** Every step, tool call, and result is visible to the user
- **User-in-the-Loop:** Users can intervene, approve, or request changes at any step

### 2. Real-Time, Cursor-Like Transparency
- **Live Progress:** All backend actions are streamed to the frontend in real-time
- **Tool Call Visibility:** Users see which tools are being called and with what arguments
- **Result Streaming:** Outputs and previews appear as soon as they're generated
- **Status Indicators:** Clear progress bars, status icons, and completion indicators

### 3. Strong Context Management
- **User Preferences:** Remember and apply user settings across sessions
- **Adaptive Behavior:** Adjust approval frequency and workflow based on user patterns
- **Style Learning:** Maintain and apply user's preferred video styles and voices
- **Session Memory:** Track successful patterns and user feedback

### 4. Local-First, Privacy-Focused
- **Local Processing:** All data and files remain on the user's device
- **No Cloud Dependencies:** Works completely offline
- **Secure File Management:** Proper sandboxing and input validation
- **User Control:** Complete control over data and privacy

---

## User Experience Guidelines

### 1. Continuous Process with User Control

**Standard Flow:**
- AI runs the entire process automatically based on user preferences
- Users can see all progress in real-time
- Process continues until completion unless interrupted
- Best for users who want automated creation with oversight

**User Interruption:**
- Users can stop the process at any time with a "Stop" button
- When stopped, users can make changes to any generated content
- Users can resume the process when ready
- Best for users who want control over the creation process

**Error Recovery:**
- If AI encounters issues, it asks for user help
- Users can provide suggestions or manual input
- Process continues once issue is resolved
- Ensures robust handling of edge cases

### 2. Real-Time Feedback

**Progress Visualization:**
- Progress bars for each step
- Status icons (✅, ❌, ⏳, 🤔)
- Live previews of generated content
- Tool call details and arguments

**Error Handling:**
- Clear error messages with context
- Retry options with different parameters
- User help requests when AI is stuck
- Graceful degradation and fallbacks

**Process Control:**
- Stop/Resume buttons for user control
- Ability to modify any generated content when paused
- Clear indication of process state (running/paused)
- Resume functionality with updated content

### 3. Content Organization

**File Management:**
- Organized by session/project
- Clear file types and metadata
- Search and filter capabilities
- Thumbnail previews for all media

**Timeline Visualization:**
- Real-time timeline updates
- Visual indicators for effects and transitions
- Audio track visualization
- Clip duration and placement markers

---

## Real-Time GUI Integration Requirements

### ⚠️ CRITICAL: All Backend Changes Must Be Immediately Visible in GUI

**Script Tab Integration:**
- Generated scripts automatically appear in the Script tab with live updates
- Script content is editable and changes are synced back to orchestrator
- Script generation progress shows real-time typing/creation effect
- Script preview shows syntax highlighting and formatting

**Project Files Tab Integration:**
- All downloaded B-roll files immediately appear in Project Files tab with thumbnails
- Generated audio files (voiceovers) appear with waveform previews
- Video assets show duration, resolution, and preview thumbnails
- File organization by type (video, audio, images, scripts) with search/filter
- File metadata (size, format, duration) displayed for each asset

**Video Preview Area Integration:**
- Generated videos automatically load in the video preview area
- Video preview only shows downloaded/playing content (never empty during generation)
- Real-time preview updates as video assembly progresses
- Preview shows current state of video with applied effects/transitions
- Video controls (play, pause, seek, volume) for preview functionality

**Effects/Transitions/Filters/Voices Integration:**
- All available effects, transitions, filters, and voices are selectable in prompt area
- Applied effects show visual previews and can be adjusted
- Voice selection shows available voices with audio previews
- Filter effects show before/after previews
- Effects library with categories and search functionality

**Timeline Integration:**
- Video timeline updates in real-time as clips are added/assembled
- Applied effects and transitions show on timeline with visual indicators
- Audio tracks show voiceover placement and timing
- Timeline shows clip durations, transitions, and effect markers

**Chat/Interaction Panel Integration:**
- All orchestrator messages stream in real-time
- Tool calls and results are transparently displayed
- Stop/Resume buttons for user control
- Error messages and retry options are clearly presented
- Progress updates show current step and completion percentage

**Settings/Preferences Panel Integration:**
- User preferences are immediately reflected in orchestrator behavior
- Style preferences affect tool parameters in real-time
- Quality settings adjust tool execution parameters
- Process control settings for user interruption behavior

---

## Technical Design Guidelines

### 1. Backend Architecture

**Orchestrator Design:**
- State machine for workflow management
- Async/await for non-blocking operations
- WebSocket/SSE for real-time streaming
- Dual-response pattern (user message + tool call)

**Tool Abstraction:**
- Standard interface for all tools
- Input/output validation with schemas
- Error handling and retry logic
- Timeout protection for long-running operations

**State Management:**
- In-memory session state for performance
- Persistent storage for session history
- Context vector embeddings for similarity
- User preference storage and retrieval

### 2. Frontend Architecture

**Real-Time Updates:**
- WebSocket client with reconnection logic
- Message type handlers for different updates
- State synchronization with backend
- Progress visualization components

**Component Design:**
- Modular, reusable components
- Responsive design for different screen sizes
- Accessibility compliance
- Performance optimization for large files

**User Interface:**
- Clean, modern design
- Intuitive navigation
- Clear visual hierarchy
- Consistent interaction patterns

### 3. Data Flow

**Message Types:**
- ai_message: Agent's user-facing messages
- tool_call: Tool execution details
- tool_result: Tool output and results
- progress: Step progress and status
- process_paused: Process paused, waiting for user changes
- error: Error details and recovery options

**State Synchronization:**
- Real-time backend-to-frontend updates
- Frontend-to-backend user input
- Session state persistence
- File management synchronization

---

## Implementation Guidelines

### 1. Development Priorities

**Phase 1: Core Infrastructure**
- Backend orchestrator and state management
- Basic tool abstraction and validation
- Real-time streaming infrastructure
- File management and security

**Phase 2: Core Tools**
- Script writer with template system
- B-roll finder with local and API sources
- Voiceover generator with TTS integration
- Video processor with FFmpeg integration

**Phase 3: Frontend Development**
- Real-time UI components
- File preview and management
- User interaction and approval workflows
- Settings and preferences management

**Phase 4: Integration and Polish**
- End-to-end workflow testing
- Performance optimization
- Error handling and recovery
- Documentation and user guides

### 2. Quality Assurance

**Testing Requirements:**
- Unit tests for all tools and components
- Integration tests for end-to-end workflows
- Performance testing with large files
- Error scenario testing and recovery

**Security Considerations:**
- Input validation and sanitization
- File sandboxing and permissions
- Session security and authentication
- Data privacy and local-first principles

**Performance Requirements:**
- Real-time streaming with <100ms latency
- Support for large video files (4K, 60fps)
- Efficient memory usage for long sessions
- Responsive UI during intensive operations

---

## Success Metrics

### 1. User Experience
- Users can create videos with minimal intervention
- All steps are transparent and understandable
- Error recovery is smooth and user-friendly
- Performance meets real-time expectations

### 2. Technical Performance
- Real-time streaming works reliably
- File management is efficient and secure
- Tool execution is fast and reliable
- System handles errors gracefully

### 3. Extensibility
- New tools can be added easily
- User preferences are flexible and comprehensive
- System can adapt to different use cases
- Architecture supports future enhancements

---

## Critical Architectural Improvements

To ensure Sclip is robust, user-friendly, and reliable, the following architectural improvements are necessary:

1. **Strongly-Typed, Unified Messaging Layer**
   - Prevents frontend/backend communication bugs and ensures all messages (progress, tool call, error, etc.) are well-formed and expected. This guarantees the UI always reflects the true backend state.
2. **Unified Error Handling & User Feedback**
   - Provides users with clear, actionable error messages and recovery options. Consistent error handling builds trust and makes the app feel professional.
3. **Decoupling Orchestrator and Tools (Async/Message Bus or at least Subprocess Isolation)**
   - Prevents a slow or crashing tool from freezing the orchestrator or the entire app. Keeps the UI responsive and the orchestrator stable.
4. **Session State Persistence (DB or Event Sourcing)**
   - Ensures user progress isn’t lost if the app crashes or restarts. Enables session recovery, history, and transparency for multi-step workflows.
5. **Basic Tool Sandboxing/Security**
   - Prevents tools from accidentally or maliciously corrupting files or accessing unauthorized data. Even for local apps, this is important for safety and trust.
6. **Comprehensive Input Validation and Sanitization**
   - Prevents invalid or malicious data from breaking the app or causing security issues. Applies to all user input, API requests, and file uploads.
7. **Robust Logging and Monitoring**
   - Essential for debugging, user support, and reliability. Enables tracing issues, monitoring health, and recovering from failures.
8. **Real-Time Streaming Infrastructure**
   - Guarantees the UI is always in sync with backend actions, which is core to the Cursor-like experience.
9. **Retry Logic and Graceful Degradation**
   - Ensures the system can recover from transient failures (e.g., tool or network hiccups) without user frustration.
10. **Secure File Management and Cleanup**
    - Prevents storage bloat, data leaks, and security issues from leftover or improperly handled files. Includes per-session directories, cleanup jobs, and file validation.

---

## Conclusion

These design guidelines ensure that Sclip provides a transparent, user-controlled, and efficient video creation experience. The focus on real-time transparency, strong context management, and local-first principles creates a unique and powerful tool for AI-assisted video editing.

The implementation should prioritize user experience, technical reliability, and extensibility while maintaining the core principles of agentic orchestration and deterministic tool execution.
