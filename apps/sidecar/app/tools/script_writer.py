"""
Script Writer Tool for Sclip
Generates video scripts based on user prompts and preferences
"""
import asyncio
import json
from typing import Dict, Any
from datetime import datetime

from .base_tool import BaseTool, ToolError
from ..utils.logger import get_logger

logger = get_logger(__name__)

class ScriptWriterTool(BaseTool):
    """
    Tool for generating video scripts
    Uses template-based approach for deterministic script generation
    """
    
    def __init__(self):
        super().__init__(
            name="script_writer",
            description="Generates video scripts based on topics and style preferences",
            version="1.0.0"
        )
        
        # Enhanced script templates implementing the 5-step framework
        self.templates = {
            "cinematic": {
                "packaging": {
                    "title": "The Legend of {topic}: A Cinematic Journey",
                    "thumbnail_hook": "Discover the untold story behind {topic}",
                    "curiosity_loop": "What makes {topic} truly extraordinary?"
                },
                "outline": [
                    "The rise of {topic}",
                    "Key moments that defined {topic}",
                    "The legacy and impact of {topic}",
                    "What the future holds for {topic}"
                ],
                "intro": "In the world of {topic}, legends are born from moments that transcend the ordinary. Today, we dive deep into the story that changed everything.",
                "body": "From the early days to the pinnacle of success, {topic} represents the perfect blend of talent, determination, and sheer brilliance. Every moment, every decision, every breakthrough has led to this extraordinary journey.",
                "outro": "This is the story of {topic} - where greatness meets destiny, and where legends are made."
            },
            "documentary": {
                "packaging": {
                    "title": "The Complete Story of {topic}",
                    "thumbnail_hook": "The truth about {topic} revealed",
                    "curiosity_loop": "What really happened with {topic}?"
                },
                "outline": [
                    "The origins and background of {topic}",
                    "Key developments and milestones",
                    "Analysis of impact and significance",
                    "Current status and future implications"
                ],
                "intro": "Today, we explore the fascinating world of {topic}. Through extensive research and firsthand accounts, we uncover the complete story.",
                "body": "The journey of {topic} is one of complexity and depth. From its humble beginnings to its current prominence, every aspect tells a story of evolution and adaptation.",
                "outro": "The story of {topic} continues to unfold, shaping our understanding and leaving an indelible mark on history."
            },
            "social_media": {
                "packaging": {
                    "title": "🔥 {topic} EXPOSED: The Truth You Need to Know! 🔥",
                    "thumbnail_hook": "This {topic} story will SHOCK you!",
                    "curiosity_loop": "What REALLY happened with {topic}?"
                },
                "outline": [
                    "The shocking truth about {topic}",
                    "What they don't want you to know",
                    "The real story behind {topic}",
                    "Why this matters to YOU"
                ],
                "intro": "You won't BELIEVE what happened with {topic}! This story is absolutely INSANE and you need to see this right now!",
                "body": "Here's everything you need to know about {topic}. The details are mind-blowing and will completely change how you think about this topic.",
                "outro": "Don't forget to like, comment, and subscribe for more incredible {topic} content! Share this with your friends!"
            },
            "educational": {
                "packaging": {
                    "title": "Master {topic}: The Complete Guide",
                    "thumbnail_hook": "Learn {topic} in minutes",
                    "curiosity_loop": "What secrets does {topic} hold?"
                },
                "outline": [
                    "Understanding the basics of {topic}",
                    "Key principles and concepts",
                    "Practical applications and examples",
                    "Advanced techniques and tips"
                ],
                "intro": "Welcome to our comprehensive guide on {topic}. Whether you're a beginner or advanced learner, this guide will take your knowledge to the next level.",
                "body": "Let's break down the key concepts of {topic} step by step. We'll cover everything from fundamentals to advanced techniques.",
                "outro": "Now you have a solid understanding of {topic}. Keep practicing and exploring to master these concepts!"
            }
        }
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Define the input schema for script generation"""
        return {
            "topic": {
                "type": "string",
                "required": True,
                "description": "The main topic for the script"
            },
            "style": {
                "type": "string",
                "required": False,
                "description": "Script style (cinematic, documentary, social_media, educational)",
                "default": "cinematic"
            },
            "length": {
                "type": "string",
                "required": False,
                "description": "Script length (short, medium, long)",
                "default": "medium"
            },
            "tone": {
                "type": "string",
                "required": False,
                "description": "Script tone (professional, casual, energetic, calm)",
                "default": "professional"
            },
            "include_hooks": {
                "type": "boolean",
                "required": False,
                "description": "Whether to include attention-grabbing hooks",
                "default": True
            },
            "target_audience": {
                "type": "string",
                "required": False,
                "description": "Target audience (general, sports_fans, tech_enthusiasts, students, professionals)",
                "default": "general"
            },
            "include_call_to_action": {
                "type": "boolean",
                "required": False,
                "description": "Whether to include call-to-action in outro",
                "default": True
            },
            "include_transitions": {
                "type": "boolean",
                "required": False,
                "description": "Whether to include transition phrases between sections",
                "default": True
            },
            "pain_point": {
                "type": "string",
                "required": False,
                "description": "The main pain point or problem the video solves for viewers",
                "default": ""
            },
            "contrarian_take": {
                "type": "string",
                "required": False,
                "description": "A contrarian or novel perspective that challenges common beliefs",
                "default": ""
            },
            "use_psychology": {
                "type": "boolean",
                "required": False,
                "description": "Whether to use advanced psychological tactics (expectation vs reality, pain points, trust building)",
                "default": True
            },
            "value_proposition": {
                "type": "string",
                "required": False,
                "description": "The unique value or solution the video provides",
                "default": ""
            },
            "social_proof": {
                "type": "string",
                "required": False,
                "description": "Social proof elements (testimonials, statistics, endorsements)",
                "default": ""
            }
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Define the output schema for script generation"""
        return {
            "script_text": {
                "type": "string",
                "required": True,
                "description": "The generated script text"
            },
            "file_path": {
                "type": "string",
                "required": True,
                "description": "Path to the saved script file"
            },
            "duration": {
                "type": "float",
                "required": True,
                "description": "Estimated script duration in seconds"
            },
            "word_count": {
                "type": "integer",
                "required": True,
                "description": "Number of words in the script"
            },
            "style_used": {
                "type": "string",
                "required": True,
                "description": "The style template used"
            },
            "packaging": {
                "type": "object",
                "required": True,
                "description": "Video packaging elements (title, thumbnail hook, curiosity loop)"
            },
            "outline": {
                "type": "array",
                "required": True,
                "description": "Script outline with key points"
            },
            "sections": {
                "type": "object",
                "required": True,
                "description": "Individual script sections (intro, body, outro)"
            },
            "transitions": {
                "type": "array",
                "required": False,
                "description": "Transition phrases between sections"
            }
        }
    
    async def create_script(self, topic: str, style: str = "cinematic", length: str = "medium") -> Dict[str, Any]:
        """Create a script - wrapper for the run method to match AI agent expectations"""
        try:
            # Prepare input data for the run method
            input_data = {
                "topic": topic,
                "style": style,
                "length": length,
                "tone": "professional",
                "include_hooks": True,
                "target_audience": "general",
                "include_call_to_action": True,
                "include_transitions": True,
                "use_psychology": True
            }
            
            # Call the run method
            result = await self.run(input_data)
            
            # Return the script text for the AI agent
            return result.get("script_text", "")
            
        except Exception as e:
            logger.error(f"Error in create_script: {e}")
            raise

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a script based on input parameters using the 5-step framework"""
        try:
            # Extract input parameters
            topic = input_data.get("topic", "general topic")
            style = input_data.get("style", "cinematic")
            length = input_data.get("length", "medium")
            tone = input_data.get("tone", "professional")
            include_hooks = input_data.get("include_hooks", True)
            target_audience = input_data.get("target_audience", "general")
            include_call_to_action = input_data.get("include_call_to_action", True)
            include_transitions = input_data.get("include_transitions", True)
            pain_point = input_data.get("pain_point", "")
            contrarian_take = input_data.get("contrarian_take", "")
            use_psychology = input_data.get("use_psychology", True)
            value_proposition = input_data.get("value_proposition", "")
            social_proof = input_data.get("social_proof", "")
            
            # Validate style
            if style not in self.templates:
                style = "cinematic"
                logger.warning(f"Unknown style '{input_data.get('style')}', using 'cinematic'")
            
            # Get template
            template = self.templates[style]
            
            # Step 1: Packaging (idea, title, thumbnail)
            packaging = self._generate_packaging(template["packaging"], topic, target_audience)
            
            # Step 2: Outline (unique points)
            outline = self._generate_outline(template["outline"], topic, length)
            
            # Step 3: Intro (curiosity loop, click confirmation)
            intro = self._generate_intro(template["intro"], topic, tone, include_hooks, target_audience, 
                                       pain_point, contrarian_take, use_psychology, value_proposition, social_proof)
            
            # Step 4: Body (value delivery, rehooking)
            body = self._generate_body(template["body"], topic, tone, length, outline, include_transitions,
                                     use_psychology, value_proposition, pain_point)
            
            # Step 5: Outro (high note, call-to-action)
            outro = self._generate_outro(template["outro"], topic, tone, include_call_to_action, target_audience,
                                       use_psychology, value_proposition, pain_point)
            
            # Generate transitions if requested
            transitions = []
            if include_transitions:
                transitions = self._generate_transitions(tone, style)
            
            # Combine sections
            script_text = f"{intro}\n\n{body}\n\n{outro}"
            
            # Calculate metrics
            word_count = len(script_text.split())
            duration = self._estimate_duration(word_count, tone)
            
            # Save script to file
            file_path = self._save_script(script_text, topic, style)
            
            logger.info(f"Generated script for topic '{topic}' in {style} style using 5-step framework")
            
            return {
                "script_text": script_text,
                "file_path": file_path,
                "duration": duration,
                "word_count": word_count,
                "style_used": style,
                "packaging": packaging,
                "outline": outline,
                "sections": {
                    "intro": intro,
                    "body": body,
                    "outro": outro
                },
                "transitions": transitions,
                "metadata": {
                    "topic": topic,
                    "style": style,
                    "length": length,
                    "tone": tone,
                    "include_hooks": include_hooks,
                    "target_audience": target_audience,
                    "include_call_to_action": include_call_to_action,
                    "include_transitions": include_transitions,
                    "use_psychology": use_psychology,
                    "pain_point": pain_point,
                    "contrarian_take": contrarian_take,
                    "value_proposition": value_proposition,
                    "social_proof": social_proof,
                    "generated_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating script: {e}")
            raise ToolError(f"Failed to generate script: {e}", "SCRIPT_GENERATION_ERROR")
    
    def _generate_packaging(self, template: Dict[str, str], topic: str, target_audience: str) -> Dict[str, str]:
        """Step 1: Generate packaging (title, thumbnail hook, curiosity loop)"""
        packaging = {}
        
        # Generate title
        packaging["title"] = template["title"].format(topic=topic)
        
        # Generate thumbnail hook
        packaging["thumbnail_hook"] = template["thumbnail_hook"].format(topic=topic)
        
        # Generate curiosity loop
        packaging["curiosity_loop"] = template["curiosity_loop"].format(topic=topic)
        
        # Add audience-specific elements
        if target_audience != "general":
            audience_hooks = {
                "sports_fans": f"Every {target_audience} needs to see this!",
                "tech_enthusiasts": f"The tech behind {topic} is revolutionary!",
                "students": f"Learn {topic} in the most engaging way possible!",
                "professionals": f"The professional insights on {topic} you've been waiting for!"
            }
            packaging["audience_hook"] = audience_hooks.get(target_audience, "")
        
        return packaging
    
    def _generate_outline(self, template: list, topic: str, length: str) -> list:
        """Step 2: Generate outline with unique points"""
        outline = []
        
        # Use template outline as base
        for point in template:
            outline.append(point.format(topic=topic))
        
        # Add length-specific points
        length_points = {
            "short": 1,
            "medium": 2,
            "long": 3
        }
        
        additional_points = length_points.get(length, 2)
        for i in range(additional_points):
            outline.append(f"Additional insight {i+1} about {topic}")
        
        return outline
    
    def _generate_intro(self, template: str, topic: str, tone: str, include_hooks: bool, target_audience: str,
                       pain_point: str, contrarian_take: str, use_psychology: bool, value_proposition: str, social_proof: str) -> str:
        """Step 3: Generate intro with psychological tactics (click confirmation, curiosity loop, trust building)"""
        
        # Start with click confirmation (immediately restate what title promises)
        click_confirmation = f"You clicked on this video about {topic}, and I'm going to deliver exactly what you came for."
        
        # Set context clearly
        context = template.format(topic=topic)
        
        intro_parts = [click_confirmation, context]
        
        if use_psychology:
            # Address pain point if provided
            if pain_point:
                pain_section = f"Most people struggle with {pain_point}. You know exactly what I'm talking about - it's frustrating, it's time-consuming, and it's holding you back."
                intro_parts.append(pain_section)
            
            # Establish common belief and introduce contrarian take
            if contrarian_take:
                common_belief = f"Everyone thinks they understand {topic}. They believe the conventional wisdom, follow the same old advice, and wonder why they're not getting the results they want."
                contrarian_intro = f"But here's what they're missing: {contrarian_take}"
                intro_parts.extend([common_belief, contrarian_intro])
            
            # Build trust with social proof
            if social_proof:
                trust_builder = f"Before we dive in, here's why you should trust what I'm about to tell you: {social_proof}"
                intro_parts.append(trust_builder)
            
            # Add value proposition
            if value_proposition:
                value_intro = f"By the end of this video, you'll have {value_proposition} - something that will completely change how you approach {topic}."
                intro_parts.append(value_intro)
        
        if include_hooks:
            # Generate curiosity loop based on style
            curiosity_hooks = {
                "cinematic": f"Prepare to be amazed by the incredible story of {topic}.",
                "documentary": f"Join us on an extraordinary journey into the world of {topic}.",
                "social_media": f"🔥 The TRUTH about {topic} will SHOCK you! 🔥",
                "educational": f"Today, we're going to master everything about {topic}."
            }
            
            hook = curiosity_hooks.get("cinematic", curiosity_hooks["cinematic"])
            
            # Add audience-specific confirmation
            if target_audience != "general":
                confirmations = {
                    "sports_fans": f"If you love sports, you'll love this {topic} story!",
                    "tech_enthusiasts": f"Tech lovers, this {topic} revelation is for you!",
                    "students": f"Students, this {topic} guide will change everything!",
                    "professionals": f"Professionals, this {topic} insight is game-changing!"
                }
                hook += f" {confirmations.get(target_audience, '')}"
            
            intro_parts.insert(1, hook)  # Insert hook after click confirmation
        
        # Combine all parts with proper spacing
        intro = "\n\n".join(intro_parts)
        
        return intro
    
    def _generate_body(self, template: str, topic: str, tone: str, length: str, outline: list, include_transitions: bool,
                      use_psychology: bool, value_proposition: str, pain_point: str) -> str:
        """Step 4: Generate body with psychological value delivery and rehooking"""
        body = template.format(topic=topic)
        
        # Add content based on outline points with varied structure
        additional_content = []
        
        # Create varied content for each outline point
        for i, point in enumerate(outline):
            # Create different content structures for variety
            if i == 0:
                # First point - focus on origins/beginning
                content = f"Let's start with {point.lower()}. This is where it all began - the foundation that would shape everything that followed."
            elif i == 1:
                # Second point - focus on development
                content = f"Moving forward, we see {point.lower()}. These were the defining moments that transformed potential into reality."
            elif i == 2:
                # Third point - focus on impact
                content = f"Perhaps most importantly, {point.lower()}. This is where we see the true significance of what we're exploring."
            else:
                # Additional points - focus on future/legacy
                content = f"Looking ahead, {point.lower()}. This gives us insight into what's yet to come."
            
            additional_content.append(content)
            
            # Add varied rehooking elements
            if use_psychology:
                rehooks = [
                    f"But here's what most people miss - there's a deeper story here that changes everything.",
                    f"This is where it gets really interesting. What I'm about to share will completely change your perspective.",
                    f"Wait until you hear this next part - it's the secret that separates the successful from the struggling.",
                    f"Here's the thing that most people don't realize - there's a hidden layer to this story.",
                    f"This is the moment where everything clicks into place. You'll see what I mean in just a moment."
                ]
                if i < len(outline) - 1:  # Don't add rehook after last point
                    additional_content.append(rehooks[i % len(rehooks)])
            else:
                # Standard rehooking
                rehooks = [
                    f"But that's not all - there's more to this story than meets the eye.",
                    f"Here's where it gets really interesting.",
                    f"Wait until you hear what happens next.",
                    f"This is just the beginning of the story.",
                    f"There's so much more to discover here."
                ]
                if i < len(outline) - 1:  # Don't add rehook after last point
                    additional_content.append(rehooks[i % len(rehooks)])
        
        # Add value reinforcement if using psychology
        if use_psychology and value_proposition:
            value_reinforcement = f"Remember, the goal here isn't just to learn about {topic} - it's to understand {value_proposition}. Every piece of information I'm sharing is designed to help you achieve exactly that."
            additional_content.append(value_reinforcement)
        
        # Add pain point reminder if provided
        if use_psychology and pain_point:
            pain_reminder = f"Think back to that {pain_point} we talked about at the beginning. What you're learning now is the solution to that exact problem."
            additional_content.append(pain_reminder)
        
        # Add final body paragraph
        final_paragraph = f"Exploring the depths of {topic} reveals fascinating insights that continue to captivate audiences worldwide."
        additional_content.append(final_paragraph)
        
        body = f"{body}\n\n" + "\n\n".join(additional_content)
        
        return body
    
    def _generate_outro(self, template: str, topic: str, tone: str, include_call_to_action: bool, target_audience: str,
                       use_psychology: bool, value_proposition: str, pain_point: str) -> str:
        """Step 5: Generate outro with psychological high note and call-to-action"""
        outro = template.format(topic=topic)
        
        # Add high note that reinforces the promise
        high_notes = {
            "cinematic": f"The story of {topic} is far from over - it's just beginning.",
            "documentary": f"The impact of {topic} continues to resonate across generations.",
            "social_media": f"This {topic} revelation is just the tip of the iceberg!",
            "educational": f"Your journey with {topic} has only just begun."
        }
        
        outro = f"{outro}\n\n{high_notes.get('cinematic', high_notes['cinematic'])}"
        
        # Add psychological reinforcement if enabled
        if use_psychology:
            # Reinforce that reality exceeded expectations
            expectation_reinforcement = f"Remember when you first clicked on this video? You probably thought you'd get some basic information about {topic}. But what you actually got was so much more valuable than that."
            outro = f"{outro}\n\n{expectation_reinforcement}"
            
            # Reinforce the value proposition
            if value_proposition:
                value_reinforcement = f"You now have {value_proposition} - exactly what you came for, and probably even more than you expected."
                outro = f"{outro}\n\n{value_reinforcement}"
            
            # Address the pain point resolution
            if pain_point:
                pain_resolution = f"That {pain_point} that was holding you back? You now have the solution. You have the knowledge, the strategy, and the confidence to overcome it."
                outro = f"{outro}\n\n{pain_resolution}"
        
        if include_call_to_action:
            # Add psychological call-to-action
            if use_psychology:
                # Native CTA that feels natural
                native_ctas = {
                    "cinematic": f"If you found this story of {topic} as compelling as I did, there's more where that came from.",
                    "documentary": f"If you want to dive deeper into the world of {topic}, I've got more insights waiting for you.",
                    "social_media": f"If this {topic} content blew your mind, wait until you see what's coming next!",
                    "educational": f"If you're ready to take your {topic} knowledge to the next level, I've got more resources for you."
                }
                cta = native_ctas.get("cinematic", native_ctas["cinematic"])
            else:
                # Standard call-to-action based on tone and audience
                ctas = {
                    "professional": f"Thank you for exploring {topic} with us.",
                    "casual": f"Thanks for hanging out and learning about {topic}!",
                    "energetic": f"Get ready to dive deeper into the world of {topic}!",
                    "calm": f"Take a moment to reflect on the wonders of {topic}."
                }
                cta = ctas.get(tone, ctas["professional"])
            
            # Add audience-specific CTA
            if target_audience != "general":
                audience_ctas = {
                    "sports_fans": f"Don't miss our next sports story!",
                    "tech_enthusiasts": f"Stay tuned for more tech insights!",
                    "students": f"Keep learning and growing with us!",
                    "professionals": f"Join us for more professional insights!"
                }
                cta += f" {audience_ctas.get(target_audience, '')}"
            
            outro = f"{outro}\n\n{cta}"
        
        return outro
    
    def _generate_transitions(self, tone: str, style: str) -> list:
        """Generate transition phrases between sections"""
        transitions = []
        
        # Tone-based transitions
        tone_transitions = {
            "professional": [
                "Moving forward,",
                "Furthermore,",
                "Additionally,",
                "Moreover,"
            ],
            "casual": [
                "Now, here's the thing,",
                "But wait, there's more!",
                "And get this,",
                "Here's what's crazy,"
            ],
            "energetic": [
                "But that's not all!",
                "Here's where it gets AMAZING!",
                "Wait for it...",
                "This is INSANE!"
            ],
            "calm": [
                "Let's explore further,",
                "Consider this,",
                "Think about it,",
                "Reflect on this,"
            ]
        }
        
        # Style-based transitions
        style_transitions = {
            "cinematic": [
                "The plot thickens as",
                "In a dramatic turn of events,",
                "The story takes an unexpected twist when",
                "As the narrative unfolds,"
            ],
            "documentary": [
                "Research reveals that",
                "Evidence suggests that",
                "Historical records show that",
                "Experts agree that"
            ],
            "social_media": [
                "You won't BELIEVE what happens next!",
                "This is where it gets CRAZY!",
                "The plot twist you never saw coming:",
                "Here's the SHOCKING truth:"
            ],
            "educational": [
                "Let's break this down further:",
                "Here's the key takeaway:",
                "To understand this better,",
                "The important thing to remember is:"
            ]
        }
        
        # Combine tone and style transitions
        all_transitions = tone_transitions.get(tone, tone_transitions["professional"]) + \
                         style_transitions.get(style, style_transitions["cinematic"])
        
        # Return a selection of transitions
        return all_transitions[:6]  # Return up to 6 transitions
    
    def _estimate_duration(self, word_count: int, tone: str) -> float:
        """Estimate script duration based on word count and tone"""
        # Average speaking rates (words per minute)
        speaking_rates = {
            "professional": 150,
            "casual": 180,
            "energetic": 200,
            "calm": 120
        }
        
        rate = speaking_rates.get(tone, 150)
        duration_minutes = word_count / rate
        return duration_minutes * 60  # Convert to seconds
    
    def _save_script(self, script_text: str, topic: str, style: str) -> str:
        """Save script to file"""
        import os
        
        # Create scripts directory if it doesn't exist
        scripts_dir = "temp/scripts"
        os.makedirs(scripts_dir, exist_ok=True)
        
        # Generate filename - use a short, safe topic name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Extract a short, meaningful topic name from the full topic
        if len(topic) > 50:
            # If topic is too long, extract key words
            words = topic.split()
            key_words = [word for word in words if len(word) > 3][:3]  # Take first 3 meaningful words
            safe_topic = "_".join(key_words)
        else:
            safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_topic = safe_topic.replace(' ', '_')
        
        # Limit filename length to avoid path issues
        safe_topic = safe_topic[:30]  # Max 30 characters
        filename = f"{safe_topic}_{style}_{timestamp}.txt"
        file_path = os.path.join(scripts_dir, filename)
        
        # Save script
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(script_text)
        
        logger.info(f"Script saved to {file_path}")
        return file_path 