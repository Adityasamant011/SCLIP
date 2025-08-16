import React, { useState, useEffect } from 'react';
import { 
  FolderPlus, FolderOpen, Clock, Star, Trash2, MoreHorizontal, 
  FileVideo, Calendar, HardDrive, Settings, Plus, Search,
  ArrowRight, Play, Edit3, Share2, Download, Sparkles, Zap,
  TrendingUp, Award, Target, Lightbulb, Rocket, Crown, 
  Palette, Music, Camera, Film, Video, Mic, Layers,
  Grid, List, SortAsc, Filter, RefreshCw, Eye, EyeOff, Archive
} from 'lucide-react';
import { useRealtimeStore } from '../hooks/useRealtimeStore';
import { useWebSocket } from '../hooks/useWebSocket';

interface Project {
  id: string;
  name: string;
  path: string;
  createdAt: string;
  lastModified: string;
  thumbnail?: string;
  status: 'active' | 'archived' | 'completed';
}

interface DashboardProps {
  onOpenProject: (project: Project) => void;
  onCreateProject: () => void;
}

const Dashboard: React.FC<DashboardProps> = ({ onOpenProject, onCreateProject }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'date' | 'modified'>('modified');
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Use WebSocket connection status from Zustand store
  const { connectionStatus } = useRealtimeStore();
  
  // Create a default session for the dashboard
  const defaultSessionId = 'dashboard-session';
  
  // Connect WebSocket for the dashboard
  useWebSocket({ 
    sessionId: defaultSessionId,
    onMessage: (msg) => {
      console.log('Dashboard received message:', msg);
    }
  });

  // Test WebSocket connection on component mount
  useEffect(() => {
    const testWebSocket = () => {
      console.log('Testing WebSocket connection...');
      const testWs = new WebSocket(`ws://127.0.0.1:8001/api/stream/${defaultSessionId}`);
      
      testWs.onopen = () => {
        console.log('✅ Test WebSocket connected successfully');
        testWs.close();
      };
      
      testWs.onerror = (error) => {
        console.error('❌ Test WebSocket failed:', error);
      };
      
      testWs.onclose = () => {
        console.log('Test WebSocket closed');
      };
    };
    
    // Test after a short delay to ensure component is mounted
    const timeoutId = setTimeout(testWebSocket, 1000);
    
    return () => clearTimeout(timeoutId);
  }, []);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      setIsLoading(true);
      console.log('Loading projects...');
      
      // Test the connection first
      console.log('Testing connection to:', 'http://127.0.0.1:8001/api/health');
      const healthResponse = await fetch('http://127.0.0.1:8001/api/health');
      console.log('Health check status:', healthResponse.status);
      
      if (!healthResponse.ok) {
        throw new Error(`Health check failed: ${healthResponse.status}`);
      }
      
      const healthData = await healthResponse.json();
      console.log('Health check response:', healthData);
      
      // Now try to load projects
      console.log('Fetching projects from:', 'http://127.0.0.1:8001/api/projects');
      const response = await fetch('http://127.0.0.1:8001/api/projects');
      console.log('Projects response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Projects API error response:', errorText);
        throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
      }
      
      const projectList = await response.json();
      console.log('Projects loaded:', projectList);
      setProjects(projectList as Project[]);
    } catch (error) {
      console.error('Failed to load projects:', error);
      
      // Show fallback projects if API is not available
      console.log('Showing fallback projects due to API error');
      const fallbackProjects: Project[] = [
        {
          id: 'sample-1',
          name: 'Cinematic Masterpiece',
          path: '/sample/path',
          createdAt: new Date().toISOString(),
          lastModified: new Date().toISOString(),
          status: 'active'
        },
        {
          id: 'sample-2', 
          name: 'Epic Adventure Trailer',
          path: '/demo/path',
          createdAt: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
          lastModified: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
          status: 'active'
        }
      ];
      setProjects(fallbackProjects);
      
      // Show a more user-friendly error
      alert(`Backend connection failed: ${error instanceof Error ? error.message : 'Unknown error'}\n\nShowing sample projects. Please ensure the backend server is running on port 8001.`);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredProjects = projects
    .filter(project => 
      project.name.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'date':
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
        case 'modified':
          return new Date(b.lastModified).getTime() - new Date(a.lastModified).getTime();
        default:
          return 0;
      }
    });

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) return 'Today';
    if (diffDays === 2) return 'Yesterday';
    if (diffDays <= 7) return `${diffDays - 1} days ago`;
    return date.toLocaleDateString();
  };

  const handleCreateProject = async () => {
    try {
      const projectName = prompt('Enter project name:');
      if (!projectName?.trim()) return;

      console.log('Creating project:', projectName);
      const response = await fetch('http://127.0.0.1:8001/api/projects', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: projectName }),
      });

      console.log('Create project response status:', response.status);
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
      }

      const newProject = await response.json();
      console.log('Project created:', newProject);
      setProjects(prev => [newProject as Project, ...prev]);
      onCreateProject();
    } catch (error) {
      console.error('Failed to create project:', error);
      alert('Failed to create project. Please try again.');
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    if (!confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await fetch(`http://127.0.0.1:8001/api/projects/${projectId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setProjects(prev => prev.filter(p => p.id !== projectId));
    } catch (error) {
      console.error('Failed to delete project:', error);
      alert('Failed to delete project. Please try again.');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
      case 'completed': return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
      case 'archived': return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
      default: return 'bg-purple-500/20 text-purple-300 border-purple-500/30';
    }
  };

  return (
    <div className="h-screen bg-gray-900 text-white flex flex-col">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">S</span>
            </div>
            <div>
              <h1 className="text-xl font-semibold text-white">Sclip</h1>
              <p className="text-sm text-gray-400">AI Video Creation Studio</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-sm">
              <div className={`w-2 h-2 rounded-full ${
                connectionStatus === 'connected' ? 'bg-green-400' : 
                connectionStatus === 'connecting' ? 'bg-yellow-400' :
                connectionStatus === 'reconnecting' ? 'bg-orange-400' : 
                'bg-red-400'
              }`}></div>
              <span className="text-gray-300">
                {connectionStatus === 'connected' ? 'Connected' : 
                 connectionStatus === 'connecting' ? 'Connecting...' :
                 connectionStatus === 'reconnecting' ? 'Reconnecting...' : 
                 'Disconnected'}
              </span>
            </div>
            <button
              onClick={handleCreateProject}
              className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
            >
              New Project
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full flex flex-col p-6">
          {/* Welcome Section */}
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-white mb-2">Welcome back</h2>
            <p className="text-gray-400">Create amazing videos with AI-powered tools</p>
          </div>

          {/* Quick Actions */}
          <div className="mb-8">
            <h3 className="text-lg font-medium text-white mb-4">Quick Actions</h3>
            <div className="grid grid-cols-3 gap-4">
              <button
                onClick={handleCreateProject}
                className="p-4 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg transition-colors group"
              >
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                    <FolderPlus className="h-4 w-4 text-white" />
                  </div>
                  <div className="text-left">
                    <div className="text-white font-medium">New Project</div>
                    <div className="text-sm text-gray-400">Start a new video project</div>
                  </div>
                </div>
              </button>

              <button
                onClick={() => {/* TODO: Import project */}}
                className="p-4 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg transition-colors group"
              >
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
                    <FolderOpen className="h-4 w-4 text-white" />
                  </div>
                  <div className="text-left">
                    <div className="text-white font-medium">Import Project</div>
                    <div className="text-sm text-gray-400">Open an existing project</div>
                  </div>
                </div>
              </button>

              <button
                onClick={() => {/* TODO: Templates */}}
                className="p-4 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg transition-colors group"
              >
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
                    <FileVideo className="h-4 w-4 text-white" />
                  </div>
                  <div className="text-left">
                    <div className="text-white font-medium">Templates</div>
                    <div className="text-sm text-gray-400">Use project templates</div>
                  </div>
                </div>
              </button>
            </div>
          </div>

          {/* Projects Section */}
          <div className="flex-1 flex flex-col min-h-0">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-white">Recent Projects</h3>
              
              <div className="flex items-center space-x-3">
                {/* View Mode Toggle */}
                <div className="flex items-center bg-gray-800 rounded-lg p-1">
                  <button
                    onClick={() => setViewMode('grid')}
                    className={`p-2 rounded-md transition-colors ${
                      viewMode === 'grid' 
                        ? 'bg-blue-500 text-white' 
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    <Grid className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setViewMode('list')}
                    className={`p-2 rounded-md transition-colors ${
                      viewMode === 'list' 
                        ? 'bg-blue-500 text-white' 
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    <List className="h-4 w-4" />
                  </button>
                </div>
                
                {/* Search */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search projects..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                  />
                </div>
                
                {/* Sort */}
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                >
                  <option value="modified">Last Modified</option>
                  <option value="date">Date Created</option>
                  <option value="name">Name</option>
                </select>
                
                {/* Refresh */}
                <button
                  onClick={loadProjects}
                  className="p-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg transition-colors"
                >
                  <RefreshCw className="h-4 w-4 text-gray-400" />
                </button>
              </div>
            </div>

            {/* Projects Content */}
            <div className="flex-1 overflow-auto">
              {isLoading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
                    <p className="text-gray-400">Loading projects...</p>
                  </div>
                </div>
              ) : filteredProjects.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <div className="w-16 h-16 bg-gray-800 rounded-lg flex items-center justify-center mx-auto mb-4">
                      <FileVideo className="h-8 w-8 text-gray-400" />
                    </div>
                    <h4 className="text-lg font-medium text-white mb-2">No projects yet</h4>
                    <p className="text-gray-400 mb-4">
                      {searchTerm ? 'No projects match your search.' : 'Create your first project to get started.'}
                    </p>
                    {!searchTerm && (
                      <button
                        onClick={handleCreateProject}
                        className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
                      >
                        Create Project
                      </button>
                    )}
                  </div>
                </div>
              ) : viewMode === 'grid' ? (
                <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {filteredProjects.map((project) => (
                    <div
                      key={project.id}
                      className="bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-750 hover:border-gray-600 transition-colors cursor-pointer group"
                      onClick={() => onOpenProject(project)}
                    >
                      {/* Project Thumbnail */}
                      <div className="h-32 bg-gray-700 rounded-t-lg flex items-center justify-center">
                        <Film className="h-8 w-8 text-gray-400" />
                      </div>
                      
                      <div className="p-4">
                        <div className="flex items-start justify-between mb-3">
                          <h4 className="text-white font-medium truncate flex-1">
                            {project.name}
                          </h4>
                          <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteProject(project.id);
                              }}
                              className="p-1 text-gray-400 hover:text-red-400 hover:bg-red-500/20 rounded transition-colors"
                            >
                              <Trash2 className="h-3 w-3" />
                            </button>
                          </div>
                        </div>

                        <div className="space-y-2 text-sm">
                          <div className="flex items-center text-gray-400">
                            <Clock className="h-3 w-3 mr-2" />
                            {formatDate(project.lastModified)}
                          </div>
                          <div className="flex items-center justify-between">
                            <span className={`px-2 py-1 rounded text-xs font-medium border ${getStatusColor(project.status)}`}>
                              {project.status}
                            </span>
                            <ArrowRight className="h-4 w-4 text-gray-400 group-hover:text-white transition-colors" />
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredProjects.map((project) => (
                    <div
                      key={project.id}
                      className="bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-750 hover:border-gray-600 transition-colors cursor-pointer p-4 group"
                      onClick={() => onOpenProject(project)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div className="w-10 h-10 bg-gray-700 rounded-lg flex items-center justify-center">
                            <Film className="h-5 w-5 text-gray-400" />
                          </div>
                          <div>
                            <h4 className="text-white font-medium">{project.name}</h4>
                            <p className="text-sm text-gray-400">Modified {formatDate(project.lastModified)}</p>
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-3">
                          <span className={`px-2 py-1 rounded text-xs font-medium border ${getStatusColor(project.status)}`}>
                            {project.status}
                          </span>
                          <ArrowRight className="h-4 w-4 text-gray-400 group-hover:text-white transition-colors" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 