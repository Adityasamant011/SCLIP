export type ApprovalMode = "auto_approve" | "major_steps_only" | "every_step";
export type ConfirmationFrequency = "low" | "medium" | "high";
export type VideoStyle = "cinematic" | "documentary" | "social_media";
export type VoiceType = "professional" | "casual" | "energetic";
export type EditingPace = "slow" | "medium" | "fast";
export type InteractionLevel = "hands_off" | "guided" | "hands_on";
export type QualitySetting = "draft" | "standard" | "high";
export type NotificationPreference = "desktop" | "email" | "silent";

export interface StylePreferences {
  video_style: VideoStyle;
  voice_type: VoiceType;
  editing_pace: EditingPace;
}

export interface UserPreferences {
  approval_mode: ApprovalMode;
  confirmation_frequency: ConfirmationFrequency;
  style_preferences: StylePreferences;
  interaction_level: InteractionLevel;
  quality_setting: QualitySetting;
  notification_preferences: NotificationPreference;
} 