#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use gcloud_sdk::google::cloud::texttospeech::v1::{
    text_to_speech_client::TextToSpeechClient, AudioConfig, AudioEncoding, ListVoicesRequest,
    SsmlVoiceGender, SynthesisInput, SynthesizeSpeechRequest, VoiceSelectionParams,
};
use gcloud_sdk::{GoogleApi, GoogleAuthMiddleware};
use std::env;

use tauri::Manager;

// Tools module moved to Python backend
// All AI orchestration is now handled by the sidecar Python backend

#[derive(Debug, serde::Serialize, serde::Deserialize, Clone)]
struct GoogleVoice {
    name: String,
    display_name: String,
    language_codes: Vec<String>,
    language_name: String,
    gender: String,
    technology: String,
    preview_path: String,
}

// Learn more about Tauri commands at https://tauri.app/v1/guides/features/command
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

// AI Orchestrator commands moved to Python backend
// These commands are now handled by the sidecar Python backend with SclipBrain orchestrator

fn get_language_display_name(lang_code: &str) -> String {
    match lang_code {
        "af-ZA" => "Afrikaans (South Africa)".to_string(),
        "ar-XA" => "Arabic".to_string(),
        "eu-ES" => "Basque (Spain)".to_string(),
        "bn-IN" => "Bengali (India)".to_string(),
        "bg-BG" => "Bulgarian (Bulgaria)".to_string(),
        "ca-ES" => "Catalan (Spain)".to_string(),
        "yue-HK" => "Chinese (Hong Kong)".to_string(),
        "cs-CZ" => "Czech (Czech Republic)".to_string(),
        "da-DK" => "Danish (Denmark)".to_string(),
        "nl-BE" => "Dutch (Belgium)".to_string(),
        "nl-NL" => "Dutch (Netherlands)".to_string(),
        "en-AU" => "English (Australia)".to_string(),
        "en-IN" => "English (India)".to_string(),
        "en-GB" => "English (UK)".to_string(),
        "en-US" => "English (US)".to_string(),
        "fil-PH" => "Filipino (Philippines)".to_string(),
        "fi-FI" => "Finnish (Finland)".to_string(),
        "fr-CA" => "French (Canada)".to_string(),
        "fr-FR" => "French (France)".to_string(),
        "gl-ES" => "Galician (Spain)".to_string(),
        "de-DE" => "German (Germany)".to_string(),
        "el-GR" => "Greek (Greece)".to_string(),
        "gu-IN" => "Gujarati (India)".to_string(),
        "he-IL" => "Hebrew (Israel)".to_string(),
        "hi-IN" => "Hindi (India)".to_string(),
        "hu-HU" => "Hungarian (Hungary)".to_string(),
        "is-IS" => "Icelandic (Iceland)".to_string(),
        "id-ID" => "Indonesian (Indonesia)".to_string(),
        "it-IT" => "Italian (Italy)".to_string(),
        "ja-JP" => "Japanese (Japan)".to_string(),
        "kn-IN" => "Kannada (India)".to_string(),
        "ko-KR" => "Korean (South Korea)".to_string(),
        "lv-LV" => "Latvian (Latvia)".to_string(),
        "lt-LT" => "Lithuanian (Lithuania)".to_string(),
        "ms-MY" => "Malay (Malaysia)".to_string(),
        "ml-IN" => "Malayalam (India)".to_string(),
        "cmn-CN" => "Mandarin Chinese (China)".to_string(),
        "cmn-TW" => "Mandarin Chinese (Taiwan)".to_string(),
        "mr-IN" => "Marathi (India)".to_string(),
        "nb-NO" => "Norwegian (Norway)".to_string(),
        "pl-PL" => "Polish (Poland)".to_string(),
        "pt-BR" => "Portuguese (Brazil)".to_string(),
        "pt-PT" => "Portuguese (Portugal)".to_string(),
        "pa-IN" => "Punjabi (India)".to_string(),
        "ro-RO" => "Romanian (Romania)".to_string(),
        "ru-RU" => "Russian (Russia)".to_string(),
        "sr-RS" => "Serbian (Serbia)".to_string(),
        "sk-SK" => "Slovak (Slovakia)".to_string(),
        "es-ES" => "Spanish (Spain)".to_string(),
        "es-US" => "Spanish (US)".to_string(),
        "sv-SE" => "Swedish (Sweden)".to_string(),
        "ta-IN" => "Tamil (India)".to_string(),
        "te-IN" => "Telugu (India)".to_string(),
        "th-TH" => "Thai (Thailand)".to_string(),
        "tr-TR" => "Turkish (Turkey)".to_string(),
        "uk-UA" => "Ukrainian (Ukraine)".to_string(),
        "vi-VN" => "Vietnamese (Vietnam)".to_string(),
        _ => lang_code.to_string(),
    }
}

#[tauri::command]
async fn list_google_voices(app_handle: tauri::AppHandle) -> Result<Vec<GoogleVoice>, String> {
    // This assumes you have set up application-default credentials.
    // Typically, this means pointing the GOOGLE_APPLICATION_CREDENTIALS
    // environment variable to your service account key file.
    let client: GoogleApi<TextToSpeechClient<GoogleAuthMiddleware>> =
        GoogleApi::from_function(
            TextToSpeechClient::new,
            "https://texttospeech.googleapis.com",
            None,
        )
        .await
        .map_err(|e| e.to_string())?;

    let response_result = client
        .get()
        .list_voices(ListVoicesRequest {
            ..Default::default()
        })
        .await;

    match response_result {
        Ok(response) => {
            let voices = response.into_inner().voices;
            let filtered_voices = voices
                .into_iter()
                .filter(|v| {
                    let name_lower = v.name.to_lowercase();
                    name_lower.contains("neural2") ||
                    name_lower.contains("wavenet") ||
                    name_lower.contains("polyglot") ||
                    name_lower.contains("standard")
                })
                .map(|v| {
                    let name_parts: Vec<&str> = v.name.split('-').collect();
                    let technology = name_parts.get(2).cloned().unwrap_or("Standard").to_string();
                    let language_code = v.language_codes.first().cloned().unwrap_or_default();
                    let language_name = get_language_display_name(&language_code);
                    let display_name = format!("{} {}", language_name.split('(').next().unwrap_or("").trim(), name_parts.last().cloned().unwrap_or(""));

                    let gender = SsmlVoiceGender::try_from(v.ssml_gender)
                        .map(|g| format!("{:?}", g))
                        .unwrap_or_else(|_| "Neutral".to_string());

                    let preview_path = app_handle
                        .path()
                        .resolve(
                            format!("../resources/preview_cache/voice_{}.mp3", v.name),
                            tauri::path::BaseDirectory::Resource,
                        )
                        .map_or_else(
                            |_| String::new(),
                            |p| p.to_string_lossy().to_string(),
                        );

                    GoogleVoice {
                        display_name,
                        language_name,
                        technology,
                        name: v.name,
                        language_codes: v.language_codes,
                        gender,
                        preview_path,
                    }
                })
                .collect();
            Ok(filtered_voices)
        }
        Err(e) => {
            return Err(e.to_string());
        }
    }
}

#[tauri::command]
async fn synthesize_speech(
    voice_name: String, 
    language_code: String, 
    text: String
) -> Result<Vec<u8>, String> {
    let client: GoogleApi<TextToSpeechClient<GoogleAuthMiddleware>> =
        GoogleApi::from_function(
            TextToSpeechClient::new,
            "https://texttospeech.googleapis.com",
            None,
        )
        .await
        .map_err(|e| e.to_string())?;

    let synthesis_input = SynthesisInput {
        input_source: Some(gcloud_sdk::google::cloud::texttospeech::v1::synthesis_input::InputSource::Text(text)),
        custom_pronunciations: None,
    };

    let voice = VoiceSelectionParams {
        language_code,
        name: voice_name,
        ssml_gender: SsmlVoiceGender::Unspecified as i32,
        custom_voice: None,
        voice_clone: None,
    };

    let audio_config = AudioConfig {
        audio_encoding: AudioEncoding::Mp3 as i32,
        speaking_rate: 1.0,
        pitch: 0.0,
        volume_gain_db: 0.0,
        sample_rate_hertz: 0,
        effects_profile_id: vec![],
    };

    let request = SynthesizeSpeechRequest {
        input: Some(synthesis_input),
        voice: Some(voice),
        audio_config: Some(audio_config),
        advanced_voice_options: None,
    };

    let response_result = client
        .get()
        .synthesize_speech(request)
        .await;

    match response_result {
        Ok(response) => {
            let audio_content = response.into_inner().audio_content;
            Ok(audio_content)
        }
        Err(e) => {
            Err(e.to_string())
        }
    }
}



#[tauri::command]
async fn get_voice_preview_audio(app_handle: tauri::AppHandle, voice_name: String) -> Result<Vec<u8>, String> {
    use std::fs;
    
    // Look for static voice preview files in the resources/preview_cache directory
    let resource_dir = app_handle.path().resource_dir().map_err(|e| e.to_string())?;
    let cache_dir = resource_dir.join("preview_cache");
    let file_path = cache_dir.join(format!("voice_{}.mp3", voice_name));
    
    if file_path.exists() {
        fs::read(&file_path).map_err(|e| e.to_string())
    } else {
        Err(format!("Voice preview file not found: voice_{}.mp3", voice_name))
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Install the default crypto provider for rustls
    rustls::crypto::ring::default_provider()
        .install_default()
        .expect("Failed to install rustls crypto provider");

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            greet,
            list_google_voices,
            synthesize_speech,
            get_voice_preview_audio
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
