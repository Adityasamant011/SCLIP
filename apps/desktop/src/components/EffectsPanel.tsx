import React, { useState, useEffect } from "react";
import { useRealtimeStore } from "../hooks/useRealtimeStore";

interface Effect {
  id: string;
  name: string;
  description: string;
  category: string;
}

interface Transition {
  id: string;
  name: string;
  description: string;
  category: string;
}

interface Filter {
  id: string;
  name: string;
  description: string;
  category: string;
}

interface Voice {
  id: string;
  name: string;
  language: string;
  gender: string;
}

const EffectsPanel: React.FC = () => {
  const toolCalls = useRealtimeStore((s) => s.toolCalls);
  const toolResults = useRealtimeStore((s) => s.toolResults);
  const [selected, setSelected] = useState<{ effect?: string; transition?: string; filter?: string; voice?: string }>({});
  
  // State for fetched data
  const [effects, setEffects] = useState<Effect[]>([]);
  const [transitions, setTransitions] = useState<Transition[]>([]);
  const [filters, setFilters] = useState<Filter[]>([]);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch data from backend
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        console.log('🔄 Fetching effects data...');
        
        // Fetch effects
        console.log('📡 Fetching effects...');
        const effectsResponse = await fetch('http://localhost:8001/assets/effects');
        console.log('📡 Effects response status:', effectsResponse.status);
        if (effectsResponse.ok) {
          const effectsData = await effectsResponse.json();
          console.log('📡 Effects data:', effectsData);
          setEffects(effectsData.effects || []);
        } else {
          console.error('❌ Effects fetch failed:', effectsResponse.status, effectsResponse.statusText);
        }
        
        // Fetch transitions
        console.log('📡 Fetching transitions...');
        const transitionsResponse = await fetch('http://localhost:8001/assets/transitions');
        console.log('📡 Transitions response status:', transitionsResponse.status);
        if (transitionsResponse.ok) {
          const transitionsData = await transitionsResponse.json();
          console.log('📡 Transitions data:', transitionsData);
          setTransitions(transitionsData.transitions || []);
        } else {
          console.error('❌ Transitions fetch failed:', transitionsResponse.status, transitionsResponse.statusText);
        }
        
        // Fetch filters
        console.log('📡 Fetching filters...');
        const filtersResponse = await fetch('http://localhost:8001/assets/filters');
        console.log('📡 Filters response status:', filtersResponse.status);
        if (filtersResponse.ok) {
          const filtersData = await filtersResponse.json();
          console.log('📡 Filters data:', filtersData);
          setFilters(filtersData.filters || []);
        } else {
          console.error('❌ Filters fetch failed:', filtersResponse.status, filtersResponse.statusText);
        }
        
        // For now, use sample voices until we have a voices endpoint
        setVoices([
          { id: "en-US-Neural2-A", name: "US English (Neural2-A)", language: "en-US", gender: "male" },
          { id: "en-GB-Neural2-B", name: "British English (Neural2-B)", language: "en-GB", gender: "female" },
          { id: "en-US-Neural2-C", name: "US English (Neural2-C)", language: "en-US", gender: "male" },
        ]);
        
        console.log('✅ All data fetched successfully');
        
      } catch (error) {
        console.error('❌ Error fetching effects data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Find currently applied effects/transitions/filters/voices
  const appliedEffects = toolCalls.filter(c => c.message?.toLowerCase().includes("effect"));
  const appliedTransitions = toolCalls.filter(c => c.message?.toLowerCase().includes("transition"));
  const appliedFilters = toolCalls.filter(c => c.message?.toLowerCase().includes("filter"));
  const appliedVoices = toolCalls.filter(c => c.message?.toLowerCase().includes("voice"));

  function handleSelect(type: string, value: string) {
    setSelected((prev) => ({ ...prev, [type]: value }));
    // TODO: Send selection to backend/orchestrator
    console.log(`Selected ${type}: ${value}`);
  }

  function getPreviewUrl(type: string, id: string): string {
    return `http://localhost:8001/preview/${type}/${id}`;
  }

  if (loading) {
    return <div style={{ padding: 16 }}>Loading effects...</div>;
  }

  console.log('🎨 Rendering EffectsPanel with:', {
    effects: effects.length,
    transitions: transitions.length,
    filters: filters.length,
    voices: voices.length
  });

  return (
    <div style={{ padding: 16 }}>
      <h3>Effects / Transitions / Filters / Voices</h3>
      <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
        
        {/* Effects */}
        <div style={{ minWidth: 200 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Effects</div>
          <div style={{ maxHeight: 300, overflowY: "auto" }}>
            {effects.map((effect) => (
              <div key={effect.id} style={{ marginBottom: 8, padding: 8, border: "1px solid #333", borderRadius: 4 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <img 
                    src={getPreviewUrl("effect", effect.id)} 
                    alt={effect.name}
                    style={{ width: 60, height: 40, objectFit: "cover", borderRadius: 4 }}
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                    }}
                  />
                  <div style={{ flex: 1 }}>
                    <button 
                      onClick={() => handleSelect("effect", effect.id)} 
                      style={{ 
                        fontWeight: selected.effect === effect.id ? 700 : 400,
                        background: "none",
                        border: "none",
                        color: "inherit",
                        cursor: "pointer",
                        textAlign: "left",
                        width: "100%"
                      }}
                    >
                      {effect.name}
                    </button>
                    <div style={{ fontSize: "0.8em", color: "#666" }}>{effect.description}</div>
                  </div>
                </div>
                {appliedEffects.some(a => a.message?.includes(effect.name)) && 
                  <span style={{ color: "#4f8cff", fontSize: "0.8em" }}>(applied)</span>
                }
              </div>
            ))}
          </div>
        </div>

        {/* Transitions */}
        <div style={{ minWidth: 200 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Transitions</div>
          <div style={{ maxHeight: 300, overflowY: "auto" }}>
            {transitions.map((transition) => (
              <div key={transition.id} style={{ marginBottom: 8, padding: 8, border: "1px solid #333", borderRadius: 4 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <img 
                    src={getPreviewUrl("transition", transition.id)} 
                    alt={transition.name}
                    style={{ width: 60, height: 40, objectFit: "cover", borderRadius: 4 }}
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                    }}
                  />
                  <div style={{ flex: 1 }}>
                    <button 
                      onClick={() => handleSelect("transition", transition.id)} 
                      style={{ 
                        fontWeight: selected.transition === transition.id ? 700 : 400,
                        background: "none",
                        border: "none",
                        color: "inherit",
                        cursor: "pointer",
                        textAlign: "left",
                        width: "100%"
                      }}
                    >
                      {transition.name}
                    </button>
                    <div style={{ fontSize: "0.8em", color: "#666" }}>{transition.description}</div>
                  </div>
                </div>
                {appliedTransitions.some(a => a.message?.includes(transition.name)) && 
                  <span style={{ color: "#0af", fontSize: "0.8em" }}>(applied)</span>
                }
              </div>
            ))}
          </div>
        </div>

        {/* Filters */}
        <div style={{ minWidth: 200 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Filters</div>
          <div style={{ maxHeight: 300, overflowY: "auto" }}>
            {filters.map((filter) => (
              <div key={filter.id} style={{ marginBottom: 8, padding: 8, border: "1px solid #333", borderRadius: 4 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <img 
                    src={getPreviewUrl("filter", filter.id)} 
                    alt={filter.name}
                    style={{ width: 60, height: 40, objectFit: "cover", borderRadius: 4 }}
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                    }}
                  />
                  <div style={{ flex: 1 }}>
                    <button 
                      onClick={() => handleSelect("filter", filter.id)} 
                      style={{ 
                        fontWeight: selected.filter === filter.id ? 700 : 400,
                        background: "none",
                        border: "none",
                        color: "inherit",
                        cursor: "pointer",
                        textAlign: "left",
                        width: "100%"
                      }}
                    >
                      {filter.name}
                    </button>
                    <div style={{ fontSize: "0.8em", color: "#666" }}>{filter.description}</div>
                  </div>
                </div>
                {appliedFilters.some(a => a.message?.includes(filter.name)) && 
                  <span style={{ color: "#0fa", fontSize: "0.8em" }}>(applied)</span>
                }
              </div>
            ))}
          </div>
        </div>

        {/* Voices */}
        <div style={{ minWidth: 200 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Voices</div>
          <div style={{ maxHeight: 300, overflowY: "auto" }}>
            {voices.map((voice) => (
              <div key={voice.id} style={{ marginBottom: 8, padding: 8, border: "1px solid #333", borderRadius: 4 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ width: 60, height: 40, background: "#444", borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    🔊
                  </div>
                  <div style={{ flex: 1 }}>
                    <button 
                      onClick={() => handleSelect("voice", voice.id)} 
                      style={{ 
                        fontWeight: selected.voice === voice.id ? 700 : 400,
                        background: "none",
                        border: "none",
                        color: "inherit",
                        cursor: "pointer",
                        textAlign: "left",
                        width: "100%"
                      }}
                    >
                      {voice.name}
                    </button>
                    <div style={{ fontSize: "0.8em", color: "#666" }}>{voice.language} • {voice.gender}</div>
                  </div>
                </div>
                {appliedVoices.some(a => a.message?.includes(voice.name)) && 
                  <span style={{ color: "#fa0", fontSize: "0.8em" }}>(applied)</span>
                }
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default EffectsPanel; 