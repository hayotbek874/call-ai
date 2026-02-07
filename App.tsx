
import React, { useState, useEffect, useRef } from 'react';
import { GoogleGenAI, Modality, LiveServerMessage } from '@google/genai';
import { CallStatus, LanguageOption, RecordedCall } from './types';
import { encode, decode, decodeAudioData } from './utils/audio-helpers';
import { playSound } from './utils/sound-effects';

const ZARGARSHOP_PROMPT = `
Role: Sen "Zargarshop" telemagazini va onlayn-do'konining professional, samimiy va mijozga yo'naltirilgan savdo operatorisan.
Muloqot uslubi: Jonli inson kabi gaplash. Qisqa va aniq javob ber. Har bir gapni savol bilan tugat.

Bilimlar:
- Salomlashish: "Assalomu alaykum! Zargarshopga xush kelibsiz. Sizni qaysi turdagi taqinchoq qiziqtiryapti?"
- Lot raqami: Mijozdan ekranning yuqori chap burchagidagi lot raqamini so'ra.
- Mahsulot: 585-probali tillasuv yugurtirilgan. Rangi o'chmaydi. Narxi efirda: 139,000 so'm! (Aslida 1,155,000 so'm).
- Yetkazib berish: Toshkent (39,000 so'm - ertaga), Viloyatlar (49,000 so'm - 5 kungacha). Bepul emas!
- VIP Klub: 175,000 so'm evaziga 1 yil 70% chegirma + yuz massajyori sovg'a.
- To'lov: Mahsulotni olganda (Naqd yoki Payme). 14 kunlik almashtirish kafolati bor.
- Tilla haqida: Bizda sof tilla yo'q, lekin ko'rinishi bir xil va arzon.
`;

const LANGUAGES: LanguageOption[] = [
  { code: 'uz', label: 'O\'zbekcha', flag: '🇺🇿', instruction: ZARGARSHOP_PROMPT },
  { code: 'ru', label: 'Русский', flag: '🇷🇺', instruction: `Вы оператор Zargarshop. Продавайте украшения за 139,000 сум. Будьте кратки и профессиональны.` },
];

type Tab = 'call' | 'history' | 'settings';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('call');
  const [status, setStatus] = useState<CallStatus>(CallStatus.IDLE);
  const [selectedLang, setSelectedLang] = useState<LanguageOption>(LANGUAGES[0]);
  const [callDuration, setCallDuration] = useState(0);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [userSpeaking, setUserSpeaking] = useState(false);
  const [dialNumber, setDialNumber] = useState('');
  
  const audioContextInRef = useRef<AudioContext | null>(null);
  const audioContextOutRef = useRef<AudioContext | null>(null);
  const nextStartTimeRef = useRef(0);
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const micStreamRef = useRef<MediaStream | null>(null);
  const sessionRef = useRef<any>(null);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    if (status === CallStatus.ACTIVE) {
      timerRef.current = window.setInterval(() => setCallDuration(p => p + 1), 1000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [status]);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const endCall = () => {
    playSound.stopRing();
    if (sessionRef.current) sessionRef.current.close?.();
    if (micStreamRef.current) micStreamRef.current.getTracks().forEach(t => t.stop());
    sourcesRef.current.forEach(s => { try { s.stop(); } catch (e) {} });
    sourcesRef.current.clear();
    nextStartTimeRef.current = 0;
    setIsSpeaking(false);
    setUserSpeaking(false);
    playSound.disconnect();
    setStatus(CallStatus.IDLE);
    setDialNumber('');
    setCallDuration(0);
  };

  const startCall = async () => {
    if (!dialNumber && status === CallStatus.IDLE) return;
    try {
      setStatus(CallStatus.CONNECTING);
      playSound.ring(); 
      
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
      audioContextInRef.current = new AudioContext({ sampleRate: 16000 });
      audioContextOutRef.current = new AudioContext({ sampleRate: 24000 });
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStreamRef.current = stream;

      const sessionPromise = ai.live.connect({
        model: 'gemini-2.5-flash-native-audio-preview-12-2025',
        config: {
          responseModalities: [Modality.AUDIO],
          systemInstruction: selectedLang.instruction,
          speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Kore' } } },
        },
        callbacks: {
          onopen: () => {
            setTimeout(() => {
              playSound.stopRing();
              setStatus(CallStatus.ACTIVE);
              playSound.connect();
              
              const source = audioContextInRef.current!.createMediaStreamSource(micStreamRef.current!);
              const scriptProcessor = audioContextInRef.current!.createScriptProcessor(1024, 1, 1);
              scriptProcessor.onaudioprocess = (e) => {
                const inputData = e.inputBuffer.getChannelData(0);
                const volume = Math.max(...inputData.map(Math.abs));
                setUserSpeaking(volume > 0.04);
                const int16 = new Int16Array(inputData.length);
                for (let i = 0; i < inputData.length; i++) int16[i] = inputData[i] * 32768;
                const pcmBlob = { data: encode(new Uint8Array(int16.buffer)), mimeType: 'audio/pcm;rate=16000' };
                sessionPromise.then(s => s.sendRealtimeInput({ media: pcmBlob }));
              };
              source.connect(scriptProcessor);
              scriptProcessor.connect(audioContextInRef.current!.destination);
            }, 300); 
          },
          onmessage: async (m: LiveServerMessage) => {
            const audio = m.serverContent?.modelTurn?.parts[0]?.inlineData?.data;
            if (audio && audioContextOutRef.current) {
              const ctx = audioContextOutRef.current;
              nextStartTimeRef.current = Math.max(nextStartTimeRef.current, ctx.currentTime);
              const buffer = await decodeAudioData(decode(audio), ctx, 24000, 1);
              const src = ctx.createBufferSource();
              src.buffer = buffer;
              src.connect(ctx.destination);
              setIsSpeaking(true);
              src.onended = () => {
                sourcesRef.current.delete(src);
                if (sourcesRef.current.size === 0) setIsSpeaking(false);
              };
              src.start(nextStartTimeRef.current);
              nextStartTimeRef.current += buffer.duration;
              sourcesRef.current.add(src);
            }
          },
          onerror: () => endCall(),
          onclose: () => endCall()
        }
      });
      sessionRef.current = await sessionPromise;
    } catch (e) { endCall(); }
  };

  const navItems = [
    { id: 'call', icon: 'phone', label: 'Aloqa' },
    { id: 'history', icon: 'clock', label: 'Tarix' },
    { id: 'settings', icon: 'gear', label: 'Sozlama' }
  ];

  return (
    <div className="fixed inset-0 bg-[#020203] text-white font-sans overflow-hidden flex flex-col md:flex-row">
      {/* SIDEBAR - Compact */}
      <aside className="hidden md:flex w-20 flex-col items-center py-6 border-r border-white/5 bg-[#08080a] shrink-0">
        <div className="w-10 h-10 bg-gradient-to-tr from-indigo-600 to-purple-500 rounded-lg flex items-center justify-center mb-8">
          <i className="fa-solid fa-gem text-lg"></i>
        </div>
        <nav className="flex flex-col space-y-6">
          {navItems.map(item => (
            <button 
              key={item.id} 
              onClick={() => setActiveTab(item.id as Tab)} 
              className={`flex flex-col items-center transition-all ${activeTab === item.id ? 'text-indigo-400' : 'text-zinc-600'}`}
            >
              <i className={`fa-solid fa-${item.icon} text-lg mb-1`}></i>
              <span className="text-[7px] font-black uppercase tracking-tighter">{item.label}</span>
            </button>
          ))}
        </nav>
      </aside>

      <main className="flex-1 relative flex items-center justify-center p-1 md:p-4 overflow-hidden">
        {activeTab === 'call' ? (
          <div className="relative w-full max-w-[310px] md:max-w-[340px] h-full max-h-[640px] md:max-h-[740px] bg-black rounded-[44px] border-[8px] border-[#1c1c1e] shadow-2xl overflow-hidden ring-1 ring-white/10 flex flex-col">
            
            <div className={`absolute inset-0 bg-gradient-to-b from-indigo-950/20 via-black to-black transition-all ${status !== CallStatus.IDLE ? 'opacity-100' : 'opacity-40'}`}></div>

            {/* NOTCH AREA */}
            <div className="h-10 w-full flex items-center justify-between px-8 z-20 shrink-0">
              <span className="text-[12px] font-bold">9:41</span>
              <div className="w-20 h-5 bg-black rounded-full"></div>
              <div className="flex items-center space-x-1.5 opacity-60">
                <i className="fa-solid fa-signal text-[9px]"></i>
                <i className="fa-solid fa-battery-full text-[10px]"></i>
              </div>
            </div>

            {status === CallStatus.IDLE ? (
              <div className="flex-1 flex flex-col z-10 px-6 overflow-hidden">
                {/* COMPACT HEADER */}
                <div className="mt-2 md:mt-4 text-center shrink-0">
                  <h1 className="text-[26px] md:text-[32px] font-black tracking-tight leading-none mb-1">Zargarshop</h1>
                  <p className="text-indigo-400 font-black uppercase tracking-[0.2em] text-[7px]">AI Operator v2.1</p>
                </div>

                <div className="mt-2 flex justify-center shrink-0">
                  <button className="px-3 py-1 bg-white/5 rounded-full border border-white/10 flex items-center space-x-1.5">
                    <span className="text-xs">{selectedLang.flag}</span>
                    <span className="text-[9px] font-black tracking-widest">{selectedLang.label.toUpperCase()}</span>
                  </button>
                </div>

                {/* MAIN DIALER BODY */}
                <div className="flex-1 flex flex-col justify-around py-4 min-h-0">
                  {/* Number Display */}
                  <div className="relative w-full flex items-center justify-center h-10 shrink-0">
                    <div className="text-2xl md:text-3xl font-light text-white truncate max-w-[80%]">{dialNumber || <span className="opacity-10">Raqam...</span>}</div>
                    {dialNumber && (
                      <button onClick={() => setDialNumber(d => d.slice(0, -1))} className="absolute right-0 text-zinc-500 hover:text-white px-2">
                        <i className="fa-solid fa-delete-left"></i>
                      </button>
                    )}
                  </div>

                  {/* GRID 4x3 - Correct 0 placement */}
                  <div className="grid grid-cols-3 gap-x-4 gap-y-2 shrink-0">
                    {[
                      { n: '1', l: ' ' }, { n: '2', l: 'ABC' }, { n: '3', l: 'DEF' },
                      { n: '4', l: 'GHI' }, { n: '5', l: 'JKL' }, { n: '6', l: 'MNO' },
                      { n: '7', l: 'PQRS' }, { n: '8', l: 'TUV' }, { n: '9', l: 'WXYZ' },
                      { n: '*', l: ' ' }, { n: '0', l: '+' }, { n: '#', l: ' ' }
                    ].map(item => (
                      <button 
                        key={item.n} 
                        onClick={() => { playSound.keyPress(); setDialNumber(d => d + item.n); }} 
                        className="w-[52px] h-[52px] md:w-[60px] md:h-[60px] rounded-full bg-zinc-900/50 border border-white/5 flex flex-col items-center justify-center active:bg-zinc-700 transition-all shadow-sm mx-auto"
                      >
                        <span className="text-xl md:text-2xl leading-none">{item.n}</span>
                        <span className="text-[6px] opacity-20 tracking-tighter uppercase">{item.l}</span>
                      </button>
                    ))}
                  </div>

                  {/* CALL BUTTON - MUST BE VISIBLE */}
                  <div className="flex justify-center pt-2 shrink-0">
                    <button 
                      onClick={startCall} 
                      className="w-14 h-14 md:w-16 md:h-16 bg-gradient-to-tr from-green-500 to-emerald-400 rounded-full flex items-center justify-center text-xl md:text-2xl shadow-xl active:scale-90 transition-all"
                    >
                      <i className="fa-solid fa-phone"></i>
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              /* ACTIVE CALL - Same logic */
              <div className="flex-1 flex flex-col z-10 p-6 min-h-0">
                <div className="text-center mt-4 shrink-0">
                  <div className="w-16 h-16 bg-zinc-900 rounded-full mx-auto mb-4 flex items-center justify-center border border-white/10">
                    <i className="fa-solid fa-user text-2xl text-zinc-600"></i>
                  </div>
                  <h2 className="text-xl font-black truncate">{dialNumber || 'Zargarshop AI'}</h2>
                  <p className="text-indigo-400 font-bold uppercase text-[8px] mt-1">
                    {status === CallStatus.CONNECTING ? 'BOG\'LANISH...' : formatDuration(callDuration)}
                  </p>
                </div>

                <div className="flex-1 flex flex-col items-center justify-center min-h-0">
                  <div className="flex items-center space-x-1.5 h-20">
                    {[...Array(8)].map((_, i) => (
                      <div 
                        key={i} 
                        className="w-1 rounded-full bg-indigo-500/80 transition-all duration-150"
                        style={{ height: isSpeaking ? `${15 + Math.random() * 50}px` : userSpeaking ? `${8 + Math.random() * 25}px` : '4px' }}
                      ></div>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-y-6 mb-6 px-2 shrink-0">
                  {[
                    { icon: 'microphone-slash', l: 'Mute' },
                    { icon: 'table-cells', l: 'Keypad' },
                    { icon: 'volume-high', l: 'Speaker' },
                    { icon: 'plus', l: 'Add' },
                    { icon: 'video', l: 'Video' },
                    { icon: 'address-book', l: 'Contacts' }
                  ].map((btn, i) => (
                    <div key={i} className="flex flex-col items-center opacity-40">
                      <div className="w-10 h-10 bg-white/5 rounded-full flex items-center justify-center mb-1 border border-white/5">
                        <i className={`fa-solid fa-${btn.icon} text-xs`}></i>
                      </div>
                      <span className="text-[6px] font-black uppercase text-center">{btn.l}</span>
                    </div>
                  ))}
                </div>

                <div className="flex justify-center mb-6 shrink-0">
                  <button onClick={endCall} className="w-14 h-14 md:w-16 md:h-16 bg-red-500 rounded-full flex items-center justify-center text-xl md:text-2xl active:scale-90 transition-all">
                    <i className="fa-solid fa-phone-slash"></i>
                  </button>
                </div>
              </div>
            )}

            <div className="h-6 w-full flex items-center justify-center shrink-0">
              <div className="w-24 h-1 bg-white/10 rounded-full"></div>
            </div>
          </div>
        ) : (
          <div className="w-full max-w-xl bg-[#08080a] rounded-[32px] p-6 border border-white/5 overflow-y-auto max-h-full">
             <h2 className="text-xl font-black mb-4">{activeTab === 'settings' ? 'SOZLAMALAR' : 'TARIX'}</h2>
             {activeTab === 'settings' && (
               <div className="space-y-3">
                 {LANGUAGES.map(l => (
                   <button key={l.code} onClick={() => setSelectedLang(l)} className={`w-full flex items-center justify-between p-4 rounded-xl border transition-all ${selectedLang.code === l.code ? 'bg-indigo-600/20 border-indigo-500' : 'bg-white/5 border-white/5 text-zinc-500'}`}>
                     <div className="flex items-center space-x-3">
                       <span className="text-xl">{l.flag}</span>
                       <span className="font-bold">{l.label}</span>
                     </div>
                     {selectedLang.code === l.code && <i className="fa-solid fa-check text-indigo-400"></i>}
                   </button>
                 ))}
               </div>
             )}
          </div>
        )}
      </main>

      {/* MOBILE NAV - Ultra Compact */}
      <nav className="md:hidden bg-[#08080a] border-t border-white/5 flex items-center justify-around py-2 shrink-0">
        {navItems.map(item => (
          <button key={item.id} onClick={() => setActiveTab(item.id as Tab)} className={`flex flex-col items-center ${activeTab === item.id ? 'text-indigo-400' : 'text-zinc-600'}`}>
            <i className={`fa-solid fa-${item.icon} text-base`}></i>
            <span className="text-[7px] font-black uppercase tracking-tighter">{item.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
};

export default App;
