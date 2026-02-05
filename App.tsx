
import React, { useState, useEffect, useRef } from 'react';
import { GoogleGenAI, Modality, LiveServerMessage } from '@google/genai';
import { CallStatus, TranscriptionPart, LanguageOption, RecordedCall } from './types';
import { encode, decode, decodeAudioData } from './utils/audio-helpers';
import { playSound } from './utils/sound-effects';
import { saveAudioBlob, getAudioBlob, deleteAudioBlob } from './utils/db';

const LANGUAGES: LanguageOption[] = [
  { 
    code: 'uz', label: 'O\'zbekcha', flag: '🇺🇿', 
    instruction: 'Siz "Stratix" ismli professional operatorisiz. O\'zbek tilida juda xushmuomala va tabiiy gapiring.' 
  },
  { 
    code: 'en', label: 'English', flag: '🇺🇸', 
    instruction: 'You are "Stratix", a professional AI call operator. Speak English fluently, naturally, and professionally.' 
  },
  { 
    code: 'ru', label: 'Русский', flag: '🇷🇺', 
    instruction: 'Вы — "Стратикс", профессиональный оператор. Говорите на русском языке вежливо и естественно.' 
  },
  { 
    code: 'tr', label: 'Türkçe', flag: '🇹🇷', 
    instruction: 'Siz "Stratix" adında profesyonel bir operatörsünüz. Türkçe dilinde nazik ve akıcı konuşun.' 
  },
];

type Tab = 'call' | 'history' | 'settings';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('call');
  const [status, setStatus] = useState<CallStatus>(CallStatus.IDLE);
  const [selectedLang, setSelectedLang] = useState<LanguageOption>(LANGUAGES[0]);
  const [transcriptions, setTranscriptions] = useState<TranscriptionPart[]>([]);
  const [currentInputText, setCurrentInputText] = useState('');
  const [currentOutputText, setCurrentOutputText] = useState('');
  const [callDuration, setCallDuration] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [history, setHistory] = useState<RecordedCall[]>([]);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [dialNumber, setDialNumber] = useState('');
  const [activeKey, setActiveKey] = useState<string | null>(null);

  const audioContextInRef = useRef<AudioContext | null>(null);
  const audioContextOutRef = useRef<AudioContext | null>(null);
  const nextStartTimeRef = useRef(0);
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const micStreamRef = useRef<MediaStream | null>(null);
  const sessionRef = useRef<any>(null);
  const timerRef = useRef<number | null>(null);
  const transcriptionContainerRef = useRef<HTMLDivElement>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  // Recording specific refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordedChunksRef = useRef<globalThis.Blob[]>([]);
  const mixedDestRef = useRef<MediaStreamAudioDestinationNode | null>(null);

  useEffect(() => {
    const savedHistory = localStorage.getItem('stratix_history');
    if (savedHistory) setHistory(JSON.parse(savedHistory));
  }, []);

  useEffect(() => {
    localStorage.setItem('stratix_history', JSON.stringify(history));
  }, [history]);

  useEffect(() => {
    if (transcriptionContainerRef.current) {
      transcriptionContainerRef.current.scrollTop = transcriptionContainerRef.current.scrollHeight;
    }
  }, [transcriptions, currentInputText, currentOutputText, isProcessing]);

  useEffect(() => {
    if (status === CallStatus.ACTIVE) {
      timerRef.current = window.setInterval(() => {
        setCallDuration(prev => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      if (status === CallStatus.IDLE) setCallDuration(0);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [status]);

  // Enhanced Physical Keyboard Support
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (activeTab !== 'call' || status !== CallStatus.IDLE) return;

      const key = e.key;
      const validNumbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
      const validSpecial = ['*', '#', '+'];

      if (validNumbers.includes(key) || validSpecial.includes(key)) {
        e.preventDefault();
        handleDial(key);
        setActiveKey(key);
        setTimeout(() => setActiveKey(null), 100);
      } else if (key === 'Backspace') {
        e.preventDefault();
        handleBackspace();
        setActiveKey('backspace');
        setTimeout(() => setActiveKey(null), 100);
      } else if (key === 'Enter') {
        e.preventDefault();
        startCall(dialNumber || 'Incoming');
      } else if (key === 'Delete') {
        e.preventDefault();
        setDialNumber('');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeTab, status, dialNumber]);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const createPCMData = (data: Float32Array) => {
    const l = data.length;
    const int16 = new Int16Array(l);
    for (let i = 0; i < l; i++) {
      int16[i] = data[i] * 32768;
    }
    return {
      data: encode(new Uint8Array(int16.buffer)),
      mimeType: 'audio/pcm;rate=16000',
    };
  };

  const stopAllAudio = () => {
    sourcesRef.current.forEach(source => {
      try { source.stop(); } catch (e) {}
    });
    sourcesRef.current.clear();
    nextStartTimeRef.current = 0;
    setIsSpeaking(false);
  };

  const startRecording = () => {
    if (!mixedDestRef.current) return;
    recordedChunksRef.current = [];
    const recorder = new MediaRecorder(mixedDestRef.current.stream);
    
    // Capture current values for the closure
    const recordingLang = selectedLang.label;
    
    recorder.ondataavailable = (e) => e.data.size > 0 && recordedChunksRef.current.push(e.data);
    recorder.onstop = async () => {
      const blob = new globalThis.Blob(recordedChunksRef.current, { type: 'audio/webm' });
      const id = Math.random().toString(36).substr(2, 9);
      const fileName = `StratixCall_${new Date().getTime()}.webm`;
      
      try {
        await saveAudioBlob(id, blob);
      } catch (err) {
        console.error("Audio saqlashda xatolik:", err);
      }

      const newEntry: RecordedCall = {
        id,
        timestamp: new Date().toLocaleString(),
        duration: callDuration,
        language: recordingLang,
        transcriptionCount: transcriptions.length,
        fileName,
      };
      
      setHistory(prev => [newEntry, ...prev]);
      playSound.alert();
    };
    recorder.start();
    mediaRecorderRef.current = recorder;
    setIsRecording(true);
    playSound.alert();
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  };

  const downloadCall = async (item: RecordedCall) => {
    try {
      const blob = await getAudioBlob(item.id);
      if (blob) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = item.fileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      }
    } catch (err) { console.error(err); }
  };

  const playCall = async (item: RecordedCall) => {
    if (playingId === item.id) {
      audioPlayerRef.current?.pause();
      setPlayingId(null);
      return;
    }
    try {
      const blob = await getAudioBlob(item.id);
      if (blob && audioPlayerRef.current) {
        const url = URL.createObjectURL(blob);
        audioPlayerRef.current.src = url;
        audioPlayerRef.current.play();
        setPlayingId(item.id);
        audioPlayerRef.current.onended = () => {
          setPlayingId(null);
          window.URL.revokeObjectURL(url);
        };
      }
    } catch (err) { console.error(err); }
  };

  const handleDelete = async (id: string) => {
    if (confirm("Ushbu muloqotni o'chirmoqchimisiz?")) {
      await deleteAudioBlob(id);
      setHistory(prev => prev.filter(item => item.id !== id));
    }
  };

  const endCall = (shouldPlaySound = true) => {
    playSound.stopRing();
    if (isRecording) stopRecording();
    if (sessionRef.current) sessionRef.current.close?.();
    if (micStreamRef.current) micStreamRef.current.getTracks().forEach(track => track.stop());
    stopAllAudio();
    if (shouldPlaySound && (status === CallStatus.ACTIVE || status === CallStatus.CONNECTING)) playSound.disconnect();
    setStatus(CallStatus.IDLE);
    setIsProcessing(false);
    setIsSpeaking(false);
    setDialNumber('');
  };

  const startCall = async (outboundNumber?: string) => {
    try {
      setTranscriptions([]);
      setStatus(CallStatus.CONNECTING);
      playSound.ring(); 
      
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY || '' });
      audioContextInRef.current = new AudioContext({ sampleRate: 16000 });
      audioContextOutRef.current = new AudioContext({ sampleRate: 24000 });
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStreamRef.current = stream;
      const outCtx = audioContextOutRef.current;
      const mixedDest = outCtx.createMediaStreamDestination();
      mixedDestRef.current = mixedDest;
      const micSource = outCtx.createMediaStreamSource(stream);
      micSource.connect(mixedDest);

      const instruction = outboundNumber && outboundNumber !== 'Incoming'
        ? `${selectedLang.instruction}. SIZ HOZIR MIJOZGA (${outboundNumber}) TELEFON QILYAPSIZ. Mijoz go'shakni ko'targanda, o'zingizni tanishtiring va unga qanday yordam bera olishingizni so'rang. Muloqotni siz boshlang!`
        : selectedLang.instruction;

      const sessionPromise = ai.live.connect({
        model: 'gemini-2.5-flash-native-audio-preview-12-2025',
        config: {
          responseModalities: [Modality.AUDIO],
          systemInstruction: instruction,
          speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Kore' } } },
          outputAudioTranscription: {},
          inputAudioTranscription: {},
        },
        callbacks: {
          onopen: () => {
            setTimeout(() => {
              playSound.stopRing();
              setStatus(CallStatus.ACTIVE);
              playSound.connect();
              
              const source = audioContextInRef.current!.createMediaStreamSource(micStreamRef.current!);
              const scriptProcessor = audioContextInRef.current!.createScriptProcessor(4096, 1, 1);
              scriptProcessor.onaudioprocess = (e) => {
                const pcmBlob = createPCMData(e.inputBuffer.getChannelData(0));
                sessionPromise.then(s => s.sendRealtimeInput({ media: pcmBlob }));
              };
              source.connect(scriptProcessor);
              scriptProcessor.connect(audioContextInRef.current!.destination);
            }, 3000); 
          },
          onmessage: async (m: LiveServerMessage) => {
            if (m.serverContent?.inputTranscription) {
              setCurrentInputText(prev => prev + m.serverContent!.inputTranscription!.text);
              setIsProcessing(true);
            }
            if (m.serverContent?.outputTranscription) {
              setCurrentOutputText(prev => prev + m.serverContent!.outputTranscription!.text);
              setIsProcessing(false);
            }
            if (m.serverContent?.turnComplete) {
              setTranscriptions(prev => [
                ...prev,
                { id: Math.random().toString(), sender: 'user', text: currentInputText, timestamp: new Date() },
                { id: Math.random().toString(), sender: 'ai', text: currentOutputText, timestamp: new Date() }
              ]);
              setCurrentInputText('');
              setCurrentOutputText('');
              setIsProcessing(false);
            }
            const audio = m.serverContent?.modelTurn?.parts[0]?.inlineData?.data;
            if (audio && audioContextOutRef.current) {
              const ctx = audioContextOutRef.current;
              nextStartTimeRef.current = Math.max(nextStartTimeRef.current, ctx.currentTime);
              const buffer = await decodeAudioData(decode(audio), ctx, 24000, 1);
              const src = ctx.createBufferSource();
              src.buffer = buffer;
              src.connect(ctx.destination);
              src.connect(mixedDestRef.current!);
              
              setIsSpeaking(true);
              src.addEventListener('ended', () => {
                sourcesRef.current.delete(src);
                if (sourcesRef.current.size === 0) {
                  setIsSpeaking(false);
                }
              });
              
              src.start(nextStartTimeRef.current);
              nextStartTimeRef.current += buffer.duration;
              sourcesRef.current.add(src);
            }
          },
          onerror: () => { playSound.alert(); endCall(false); },
          onclose: () => endCall(false)
        }
      });
      sessionRef.current = await sessionPromise;
    } catch (e) {
      playSound.alert();
      endCall(false);
    }
  };

  const handleDial = (num: string) => {
    playSound.keyPress();
    if (dialNumber.length < 15) setDialNumber(prev => prev + num);
  };

  const handleBackspace = () => {
    playSound.keyPress();
    setDialNumber(prev => prev.slice(0, -1));
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col md:flex-row font-sans selection:bg-indigo-100 selection:text-indigo-900">
      <audio ref={audioPlayerRef} className="hidden" />
      
      {/* Sidebar Nav */}
      <aside className="w-full md:w-72 bg-white border-r border-slate-200 flex flex-col shrink-0">
        <div className="p-6 border-b border-slate-50">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center text-white shadow-lg shadow-indigo-200">
              <i className="fa-solid fa-robot"></i>
            </div>
            <div>
              <h1 className="text-lg font-black tracking-tight text-slate-800">Stratix AI</h1>
              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Operator Console</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          <button onClick={() => setActiveTab('call')} className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'call' ? 'bg-indigo-600 text-white shadow-md shadow-indigo-100' : 'text-slate-500 hover:bg-slate-50'}`}>
            <i className="fa-solid fa-headset w-5"></i>
            <span className="text-sm font-bold">Dashboard</span>
          </button>
          <button onClick={() => setActiveTab('history')} className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'history' ? 'bg-indigo-600 text-white shadow-md shadow-indigo-100' : 'text-slate-500 hover:bg-slate-50'}`}>
            <i className="fa-solid fa-clock-rotate-left w-5"></i>
            <span className="text-sm font-bold">Qo'ng'iroqlar tarixi</span>
          </button>
          <button onClick={() => setActiveTab('settings')} className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'settings' ? 'bg-indigo-600 text-white shadow-md shadow-indigo-100' : 'text-slate-500 hover:bg-slate-50'}`}>
            <i className="fa-solid fa-gear w-5"></i>
            <span className="text-sm font-bold">Sozlamalar</span>
          </button>
        </nav>

        {(status === CallStatus.ACTIVE || status === CallStatus.CONNECTING) && (
          <div className="p-4 mx-4 mb-4 bg-indigo-50 rounded-2xl border border-indigo-100">
             <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-black text-indigo-400 uppercase tracking-widest">
                  {status === CallStatus.CONNECTING ? 'Connecting...' : 'Active Call'}
                </span>
                <span className="text-xs font-mono font-bold text-indigo-600">{formatDuration(callDuration)}</span>
             </div>
             <div className="flex items-center space-x-1">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className={`h-4 w-1 bg-indigo-300 rounded-full ${status === CallStatus.ACTIVE ? 'animate-pulse' : ''}`} style={{ animationDelay: `${i * 0.1}s` }}></div>
                ))}
             </div>
          </div>
        )}

        <div className="p-6 border-t border-slate-50 flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase">
          <span>v2.5 Professional</span>
          <span className="text-green-500">Online</span>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {activeTab === 'call' && (
          <>
            <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between shrink-0">
              <h2 className="font-bold text-slate-800">
                {status === CallStatus.IDLE ? 'Yangi qo\'ng\'iroq' : 'Muloqot holati'}
              </h2>
              <div className="flex items-center space-x-2 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold text-slate-600">
                <span>{selectedLang.flag}</span>
                <span>{selectedLang.label}</span>
              </div>
            </header>

            <div ref={transcriptionContainerRef} className="flex-1 overflow-y-auto p-6 md:p-12 bg-slate-50/50">
              {status === CallStatus.IDLE ? (
                <div className="h-full flex flex-col items-center justify-center space-y-8 animate-in fade-in duration-500">
                  {/* Dialer Interface */}
                  <div className="bg-white p-8 rounded-[40px] shadow-2xl shadow-indigo-100 border border-slate-100 w-full max-w-sm">
                    <div className="mb-6 relative">
                      <input 
                        type="text" 
                        readOnly 
                        value={dialNumber}
                        placeholder="+998"
                        className={`w-full text-center text-3xl font-black text-slate-800 bg-slate-50 rounded-2xl py-6 border-2 transition-all outline-none ${activeKey ? 'border-indigo-500 scale-[1.01]' : 'border-transparent'}`}
                      />
                      {dialNumber && (
                        <button 
                          onClick={handleBackspace}
                          className={`absolute right-4 top-1/2 -translate-y-1/2 transition-colors ${activeKey === 'backspace' ? 'text-red-500 scale-110' : 'text-slate-300 hover:text-red-500'}`}
                        >
                          <i className="fa-solid fa-backspace text-xl"></i>
                        </button>
                      )}
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                      {['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#'].map((n) => (
                        <button 
                          key={n}
                          onClick={() => handleDial(n)}
                          className={`w-full aspect-square rounded-2xl bg-white border border-slate-100 text-2xl font-bold transition-all active:scale-95 shadow-sm ${activeKey === n ? 'bg-indigo-600 text-white border-indigo-600 scale-95 shadow-inner' : 'text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 hover:border-indigo-100'}`}
                        >
                          {n}
                        </button>
                      ))}
                    </div>

                    <button 
                      onClick={() => startCall(dialNumber || 'Incoming')}
                      className="w-full mt-8 py-5 bg-green-500 hover:bg-green-600 text-white rounded-2xl shadow-xl shadow-green-100 flex items-center justify-center space-x-3 transition-all hover:scale-[1.02] active:scale-95 group"
                    >
                      <i className="fa-solid fa-phone-flip text-xl group-hover:animate-bounce"></i>
                      <span className="font-black uppercase tracking-wider">Qo'ng'iroq qilish</span>
                    </button>
                  </div>
                  
                  <div className="max-w-xs text-center space-y-4">
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest leading-relaxed">
                      Klaviatura orqali raqamlarni terishingiz (0-9, *, #, Backspace, Enter) mumkin
                    </p>
                    <div className="p-3 bg-blue-50 text-blue-700 text-[10px] font-medium rounded-xl border border-blue-100 flex items-center space-x-2">
                       <i className="fa-solid fa-info-circle text-sm"></i>
                       <span>Real telefon tarmog'iga ulanish uchun VoIP xizmatlari talab etiladi.</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  {status === CallStatus.CONNECTING ? (
                    <div className="flex flex-col items-center justify-center py-10">
                       <div className="relative mb-8">
                         <div className="absolute inset-0 bg-green-500 rounded-full animate-ping opacity-20"></div>
                         <div className="w-24 h-24 bg-green-500 text-white rounded-full flex items-center justify-center text-4xl relative z-10 shadow-lg">
                           <i className="fa-solid fa-phone-volume animate-bounce"></i>
                         </div>
                       </div>
                       <div className="text-center">
                         <h3 className="text-2xl font-black text-slate-800 mb-2">
                          {dialNumber ? dialNumber : 'Mijozga bog\'lanilmoqda'}
                         </h3>
                         <p className="text-sm font-bold text-slate-400 uppercase tracking-widest animate-pulse">
                           Chaqirilmoqda...
                         </p>
                       </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center mb-10 space-y-6">
                       {/* AI Status Indicators */}
                       <div className="flex items-center space-x-8 p-6 bg-white rounded-3xl shadow-sm border border-slate-100">
                          <div className={`flex flex-col items-center space-y-2 transition-all duration-300 ${!isSpeaking && !isProcessing ? 'scale-110 opacity-100' : 'opacity-30 scale-90'}`}>
                             <div className={`w-12 h-12 rounded-full flex items-center justify-center ${!isSpeaking && !isProcessing ? 'bg-green-100 text-green-600' : 'bg-slate-50 text-slate-400'}`}>
                               <i className={`fa-solid fa-microphone-lines ${!isSpeaking && !isProcessing ? 'animate-pulse' : ''}`}></i>
                             </div>
                             <span className="text-[10px] font-black uppercase tracking-widest">Listening</span>
                          </div>
                          <div className={`flex flex-col items-center space-y-2 transition-all duration-300 ${isProcessing ? 'scale-110 opacity-100' : 'opacity-30 scale-90'}`}>
                             <div className={`w-12 h-12 rounded-full flex items-center justify-center ${isProcessing ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-50 text-slate-400'}`}>
                               <i className={`fa-solid fa-brain ${isProcessing ? 'animate-bounce' : ''}`}></i>
                             </div>
                             <span className="text-[10px] font-black uppercase tracking-widest">Processing</span>
                          </div>
                          <div className={`flex flex-col items-center space-y-2 transition-all duration-300 ${isSpeaking ? 'scale-110 opacity-100' : 'opacity-30 scale-90'}`}>
                             <div className={`w-12 h-12 rounded-full flex items-center justify-center ${isSpeaking ? 'bg-blue-100 text-blue-600' : 'bg-slate-50 text-slate-400'}`}>
                               <i className={`fa-solid fa-volume-high ${isSpeaking ? 'animate-pulse' : ''}`}></i>
                             </div>
                             <span className="text-[10px] font-black uppercase tracking-widest">Speaking</span>
                          </div>
                       </div>

                       {/* Recording Toggle */}
                       <div className="w-full max-w-xs">
                          <button 
                            onClick={() => isRecording ? stopRecording() : startRecording()}
                            className={`w-full py-3 rounded-2xl flex items-center justify-center space-x-3 border-2 transition-all shadow-lg ${isRecording ? 'bg-red-50 border-red-200 text-red-600 shadow-red-50' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}
                          >
                            <div className={`w-3 h-3 rounded-full ${isRecording ? 'bg-red-600 animate-pulse' : 'bg-slate-300'}`}></div>
                            <span className="font-black uppercase tracking-widest text-[10px]">
                              {isRecording ? 'Muloqot yozilmoqda...' : 'Muloqotni yozib olish'}
                            </span>
                          </button>
                       </div>
                    </div>
                  )}

                  {transcriptions.map((t) => (
                    <div key={t.id} className={`flex ${t.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[80%] px-5 py-3 rounded-2xl shadow-sm border ${t.sender === 'user' ? 'bg-indigo-600 text-white border-indigo-500 rounded-tr-none' : 'bg-white text-slate-800 border-slate-200 rounded-tl-none'}`}>
                        <p className="text-[15px] font-medium leading-relaxed">{t.text}</p>
                        <div className="mt-1 flex items-center justify-between opacity-50 text-[9px] font-bold uppercase">
                          <span>{t.sender === 'user' ? 'Mijoz' : 'Stratix'}</span>
                          <span>{t.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                      </div>
                    </div>
                  ))}

                  {currentInputText && (
                    <div className="flex justify-end animate-in fade-in slide-in-from-right-2">
                      <div className="bg-indigo-50 border border-indigo-200 text-indigo-900 px-5 py-3 rounded-2xl rounded-tr-none italic font-medium">
                        {currentInputText}
                      </div>
                    </div>
                  )}

                  {currentOutputText && (
                    <div className="flex justify-start animate-in fade-in slide-in-from-left-2">
                      <div className="bg-white border-2 border-indigo-100 text-slate-800 px-5 py-3 rounded-2xl rounded-tl-none font-medium">
                        {currentOutputText}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {status !== CallStatus.IDLE && (
              <footer className="p-8 bg-white border-t border-slate-200 flex items-center justify-center space-x-6 shrink-0">
                <button 
                  onClick={() => isRecording ? stopRecording() : startRecording()} 
                  className={`w-12 h-12 rounded-full border-2 transition-all flex items-center justify-center ${isRecording ? 'bg-red-500 border-red-400 text-white animate-pulse' : 'bg-white border-slate-200 text-slate-400 hover:bg-slate-50'}`}
                  title={isRecording ? "Yozishni to'xtatish" : "Yozishni boshlash"}
                >
                  <i className={`fa-solid ${isRecording ? 'fa-stop' : 'fa-record-vinyl'}`}></i>
                </button>
                <div className="w-20 h-20 bg-indigo-600 text-white rounded-full shadow-xl shadow-indigo-100 flex items-center justify-center relative">
                  {(status === CallStatus.ACTIVE || isProcessing || isSpeaking) && (
                    <div className="absolute inset-0 bg-indigo-600 rounded-full animate-ping opacity-20"></div>
                  )}
                  <i className={`fa-solid ${isProcessing ? 'fa-spinner fa-spin' : isSpeaking ? 'fa-volume-high' : 'fa-microphone'} text-2xl relative z-10`}></i>
                </div>
                <button 
                  onClick={() => endCall(true)} 
                  className="w-16 h-16 bg-red-500 hover:bg-red-600 text-white rounded-full shadow-lg shadow-red-100 flex items-center justify-center transition-all hover:scale-105 active:scale-95"
                  title="Qo'ng'iroqni tugatish"
                >
                  <i className="fa-solid fa-phone-slash text-2xl"></i>
                </button>
              </footer>
            )}
          </>
        )}

        {activeTab === 'history' && (
          <div className="flex-1 p-8 overflow-y-auto">
            <h2 className="text-2xl font-black text-slate-800 mb-6">Qo'ng'iroqlar tarixi</h2>
            {history.length === 0 ? (
              <div className="bg-white rounded-3xl p-12 text-center border border-slate-100 shadow-sm">
                 <i className="fa-solid fa-folder-open text-4xl text-slate-200 mb-4"></i>
                 <p className="text-slate-500 font-medium">Hozircha qo'ng'iroqlar mavjud emas.</p>
              </div>
            ) : (
              <div className="grid gap-4">
                {history.map((item) => (
                  <div key={item.id} className="bg-white border border-slate-100 p-5 rounded-2xl flex items-center justify-between hover:shadow-md transition-shadow group">
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-slate-50 rounded-xl flex items-center justify-center text-slate-400 group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-colors">
                        <i className={`fa-solid ${playingId === item.id ? 'fa-volume-high animate-pulse text-indigo-600' : 'fa-file-audio text-xl'}`}></i>
                      </div>
                      <div>
                        <div className="font-bold text-slate-800">{item.timestamp}</div>
                        <div className="text-xs font-bold text-slate-400 uppercase tracking-tighter">
                          {item.language} • {formatDuration(item.duration)} • {item.transcriptionCount} muloqot
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                       <button onClick={() => playCall(item)} className={`p-3 rounded-xl transition-all shadow-sm ${playingId === item.id ? 'bg-indigo-600 text-white' : 'bg-slate-50 text-slate-400 hover:bg-slate-100'}`}>
                         <i className={`fa-solid ${playingId === item.id ? 'fa-pause' : 'fa-play'}`}></i>
                       </button>
                       <button onClick={() => downloadCall(item)} className="p-3 bg-indigo-50 text-indigo-600 rounded-xl hover:bg-indigo-600 hover:text-white transition-all shadow-sm">
                         <i className="fa-solid fa-download"></i>
                       </button>
                       <button onClick={() => handleDelete(item.id)} className="p-3 bg-red-50 text-red-500 rounded-xl hover:bg-red-500 hover:text-white transition-all shadow-sm">
                         <i className="fa-solid fa-trash-can"></i>
                       </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="flex-1 p-8 overflow-y-auto max-w-2xl mx-auto w-full">
            <h2 className="text-2xl font-black text-slate-800 mb-8">Sozlamalar</h2>
            <section className="bg-white p-8 rounded-3xl border border-slate-100 shadow-sm space-y-6">
              <div>
                <label className="text-xs font-black text-slate-400 uppercase tracking-widest block mb-4">Muloqot tili</label>
                <div className="grid gap-3">
                  {LANGUAGES.map((lang) => (
                    <button key={lang.code} onClick={() => setSelectedLang(lang)} className={`flex items-center justify-between p-4 rounded-2xl border transition-all ${selectedLang.code === lang.code ? 'bg-indigo-600 text-white border-indigo-500 shadow-lg shadow-indigo-100' : 'bg-slate-50 border-slate-100 text-slate-600 hover:border-slate-300'}`}>
                      <div className="flex items-center space-x-4">
                        <span className="text-2xl">{lang.flag}</span>
                        <span className="font-bold">{lang.label}</span>
                      </div>
                      {selectedLang.code === lang.code && <i className="fa-solid fa-circle-check text-xl"></i>}
                    </button>
                  ))}
                </div>
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
