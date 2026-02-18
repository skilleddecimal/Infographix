import axios from 'axios';

const API_BASE = '/api';

export interface Entity {
  id: string;
  label: string;
  description?: string;
  layer_id?: string;
  icon_hint?: string;
}

export interface Layer {
  id: string;
  label: string;
  entity_ids: string[];
  is_cross_cutting: boolean;
}

export interface Connection {
  from_id: string;
  to_id: string;
  label?: string;
  style: string;
}

export interface Brief {
  title: string;
  subtitle?: string;
  diagram_type: string;
  entities: Entity[];
  layers: Layer[];
  connections: Connection[];
  brand_hint?: string;
  color_hint?: string;
  style_notes?: string;
  confidence: number;
}

export interface ColorPalette {
  primary: string;
  secondary: string;
  tertiary: string;
  quaternary: string;
  background: string;
  text_dark: string;
  text_light: string;
  border: string;
  connector: string;
}

export interface AnalyzeResponse {
  success: boolean;
  brief?: Brief;
  warnings: string[];
  error?: string;
}

export interface GenerateResponse {
  success: boolean;
  file_id?: string;
  download_url?: string;
  warnings: string[];
  error?: string;
}

export interface PreviewResponse {
  success: boolean;
  svg?: string;
  format: string;
  width?: number;
  height?: number;
  warnings: string[];
  error?: string;
}

export interface ArchetypeInfo {
  type: string;
  name: string;
  display_name: string;
  description: string;
  example_prompts: string[];
}

export interface BrandPreset {
  name: string;
  primary: string;
  secondary: string;
}

/**
 * Analyze a prompt using Claude to extract diagram structure.
 */
export async function analyzePrompt(prompt: string, imageBase64?: string): Promise<AnalyzeResponse> {
  const response = await axios.post<AnalyzeResponse>(`${API_BASE}/analyze`, {
    prompt,
    image_base64: imageBase64,
  });
  return response.data;
}

/**
 * Generate a PPTX file from a brief.
 */
export async function generateDiagram(
  brief: Brief,
  palette?: ColorPalette,
  brandPreset?: string
): Promise<GenerateResponse> {
  const response = await axios.post<GenerateResponse>(`${API_BASE}/generate`, {
    brief,
    palette,
    brand_preset: brandPreset,
  });
  return response.data;
}

/**
 * Generate an SVG preview from a brief.
 */
export async function previewDiagram(
  brief: Brief,
  palette?: ColorPalette,
  brandPreset?: string,
  format: 'svg' | 'data_uri' = 'svg'
): Promise<PreviewResponse> {
  const response = await axios.post<PreviewResponse>(`${API_BASE}/preview`, {
    brief,
    palette,
    brand_preset: brandPreset,
    format,
  });
  return response.data;
}

/**
 * Get list of available archetypes.
 */
export async function getArchetypes(): Promise<ArchetypeInfo[]> {
  const response = await axios.get<{ archetypes: ArchetypeInfo[] }>(`${API_BASE}/archetypes`);
  return response.data.archetypes;
}

/**
 * Get list of available brand presets.
 */
export async function getBrandPresets(): Promise<BrandPreset[]> {
  const response = await axios.get<{ presets: BrandPreset[] }>(`${API_BASE}/brands`);
  return response.data.presets;
}

/**
 * Get the download URL for a file.
 */
export function getDownloadUrl(fileId: string): string {
  return `${API_BASE}/download/${fileId}`;
}
