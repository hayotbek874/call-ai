
export interface TranscriptionPart {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: Date;
}

export interface RecordedCall {
  id: string;
  timestamp: string;
  duration: number;
  language: string;
  transcriptionCount: number;
  fileName: string;
  summary?: string;
  sentiment?: 'positive' | 'neutral' | 'negative';
  actionItems?: string[];
  followUpDraft?: string;
  transcription?: { sender: 'user' | 'ai', text: string }[];
}

export interface Contact {
  id: string;
  name: string;
  phone: string;
  addedAt: string;
}

export enum CallStatus {
  IDLE = 'IDLE',
  CONNECTING = 'CONNECTING',
  ACTIVE = 'ACTIVE',
  ENDED = 'ENDED'
}

export type LanguageCode = 'uz' | 'en' | 'ru' | 'tr';

export interface LanguageOption {
  code: LanguageCode;
  label: string;
  flag: string;
  instruction: string;
}
