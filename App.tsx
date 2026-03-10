
import React, { useState, useEffect, useRef } from 'react';
import { GoogleGenAI, Modality, LiveServerMessage, Type } from '@google/genai';
import { CallStatus, LanguageOption, RecordedCall } from './types';
import { encode, decode, decodeAudioData } from './utils/audio-helpers';
import { playSound } from './utils/sound-effects';
import { saveAudioBlob, getAudioBlob, deleteAudioBlob } from './utils/db';

const ZARGARSHOP_PROMPT = `
Sening isming: Zargar Shop AI Operatori.
Sening vazifang: "Zargar Shop" telemagazini va onlayn-do'koni mijozlariga xizmat ko'rsatish.

MULOQOT USLUBI VA INSONIYLIK (O'TA MUHIM):
- Sen shunchaki robot emassan, sen samimiy, jonli va yordamga tayyor insonga o'xshash operator bo'lishing kerak.
- Gaplaringda tabiiy to'xtalishlar, "hmm", "tushunarli", "ha, albatta", "shunaqa deng", "ha-ya", "albatta-da" kabi so'zlardan o'rinli foydalanib, muloqotni jonli qil.
- Gapni juda rasmiy boshlama. O'zbekona mehmondostlik va samimiylik bilan gaplash.
- Mijoz gapirayotganda diqqat bilan tingla. Agar mijoz seni bo'lsa, darhol to'xta va uni tingla (Barge-in).
- Ovoz ohanging iliq, xushmuomala va ishonarli bo'lsin. Xuddi yaqin do'sting bilan gaplashayotgandek samimiy bo'l.
- Mijozning kayfiyatiga qarab moslash: agar u xursand bo'lsa, sen ham ko'tarinki ruhda bo'l; agar u norozi bo'lsa, hamdardlik bildirib, muammoni hal qilishga intil.
- Qisqa javoblar berishga harakat qil, monolog o'qima. Mijoz bilan doimiy muloqotda bo'l.

QUYIDAGI QOIDALAR VA MA'LUMOTLAR ASOSIDA JAVOB BER:

1. SALOMLASHUV: "Assalomu alaykum! Siz bilan “Zargar Shop” bog‘lanmoqda. Qanday mahsulot sizga qiziq?" deb boshla. Ovozda tabassum sezilib tursin.
2. BUYURTMA: Mijoz biror narsa olmoqchi bo'lsa, har doim LOT RAQAMINI so'ra (u rasmning yuqori qismida bo'ladi).
3. LOT RAQAMI AYTILSA: "Juda ajoyib tanlov! Bu nafis mahsulot yuqori sifatli qoplama bilan ishlangan. Buyurtmani rasmiylashtirish uchun ma’lumotlaringizni qabul qilsam bo‘ladimi?" deb so'ra.
4. YETKAZIB BERISH NARXI: 
   - Toshkent shahriga: 39 000 so‘m (1 kunda yetkaziladi).
   - Viloyatlarga: 49 000 so‘m (3–5 ish kunida yetkaziladi).
5. DO'KON HAQIDA: Biz onlayn tele-magazinmiz, jismoniy do'konimiz yo'q, faqat yetkazib berish orqali ishlaymiz.
6. MAHSULOT SIFATI: 585 probali sifatli pozoleta (oltin suvi) bilan qoplangan. To‘g‘ri foydalanilsa, uzoq vaqt o‘z ko‘rinishini saqlaydi.
7. TO'LOV: Buyurtmani qabul qilganda (eshik tagida) to'lash mumkin.
8. CHEGIRMALAR: Hozirda mahsulotlarga chegirma borligini va hozir buyurtma qilsa bonus borligini ayt.
9. BUYURTMANI RASMIYLASHTIRISH: Mijoz rozi bo'lsa, Familiya, Ism va To'liq manzilini so'ra.
10. TUSHUNARSIZ HOLAT: Agar mijoz savolini tushunmasang, "Kechirasiz, yaxshi tushunmadim. So‘rovingizni qayd etib qo'ydim, mutaxassisimiz yaqin vaqt ichida siz bilan bog‘lanib, batafsil tushuntiradi" deb ayt.
11. XAYRLASHUV: "Murojaatingiz uchun katta rahmat! Kuningiz xayrli o'tsin. Agar yana savollar tug'ilsa, bemalol murojaat qiling" deb tugat.

Har bir javobing oxirida mijozga savol berib muloqotni davom ettir. Standart narxni 139,000 so'm deb hisobla.
`;

const LANGUAGES: LanguageOption[] = [
  { code: 'uz', label: 'O\'ZBEKCHA', flag: 'U Z', instruction: ZARGARSHOP_PROMPT },
  { code: 'ru', label: 'РУССКИЙ', flag: 'R U', instruction: `
Вы оператор Zargarshop. Будьте максимально человечны, используйте "хмм", "понятно", "конечно". 
Стиль общения: теплый, дружелюбный, как живой человек.
Правила: Ташкент 39к, Регионы 49к. Оплата при получении. 
Если клиент перебивает - замолчите и слушайте. 
В конце каждого ответа задавайте вопрос.` },
];

const VOICES = [
  { id: 'Zephyr', name: 'Zephyr', description: 'Yumshoq va samimiy (Tavsiya etiladi)', gender: 'Female' },
  { id: 'Kore', name: 'Kore', description: 'Aniq va professional', gender: 'Female' },
  { id: 'Puck', name: 'Puck', description: 'Quvnoq va baquvvat', gender: 'Male' },
  { id: 'Charon', name: 'Charon', description: 'Vazmin va ishonchli', gender: 'Male' },
  { id: 'Fenrir', name: 'Fenrir', description: 'Chuqur va jiddiy', gender: 'Male' },
];

type Tab = 'call' | 'history' | 'settings';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('call');
  const [status, setStatus] = useState<CallStatus>(CallStatus.IDLE);
  const [selectedLang, setSelectedLang] = useState<LanguageOption>(LANGUAGES[0]);
  const [selectedVoice, setSelectedVoice] = useState(VOICES[0]);
  const [callDuration, setCallDuration] = useState(0);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [userSpeaking, setUserSpeaking] = useState(false);
  const [dialNumber, setDialNumber] = useState('');
  const [recordings, setRecordings] = useState<RecordedCall[]>([]);
  const [fullTranscription, setFullTranscription] = useState<{ sender: 'user' | 'ai', text: string }[]>([]);
  const [transcriptionCount, setTranscriptionCount] = useState(0);
  const [lastTranscription, setLastTranscription] = useState<{ text: string, type: 'user' | 'ai' } | null>(null);
  const [customVocabulary, setCustomVocabulary] = useState('Zargar Shop, pozoleta, lot raqami, Toshkent');
  
  const [searchQuery, setSearchQuery] = useState('');
  
  const [isThinking, setIsThinking] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isOnHold, setIsOnHold] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [callError, setCallError] = useState<string | null>(null);
  
  const audioContextInRef = useRef<AudioContext | null>(null);
  const audioContextOutRef = useRef<AudioContext | null>(null);
  const nextStartTimeRef = useRef(0);
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const micStreamRef = useRef<MediaStream | null>(null);
  const sessionRef = useRef<any>(null);
  const timerRef = useRef<number | null>(null);
  const isOnHoldRef = useRef(false);
  const statusRef = useRef<CallStatus>(CallStatus.IDLE);
  
  const combinedAudioBufferRef = useRef<Float32Array[]>([]);
  const recordingDestRef = useRef<MediaStreamAudioDestinationNode | null>(null);
  const recordingProcessorRef = useRef<ScriptProcessorNode | null>(null);

  useEffect(() => {
    isOnHoldRef.current = isOnHold;
    if (isOnHold) {
      // Stop current AI audio when putting on hold
      sourcesRef.current.forEach(s => { try { s.stop(); } catch (e) {} });
      sourcesRef.current.clear();
      setIsSpeaking(false);
    }
  }, [isOnHold]);

  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const saved = localStorage.getItem('call_history');
    if (saved) setRecordings(JSON.parse(saved));
  }, []);

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

  const createWavBlob = (audioData: Float32Array[], sampleRate: number) => {
    const totalLength = audioData.reduce((acc, curr) => acc + curr.length, 0);
    const buffer = new ArrayBuffer(44 + totalLength * 2);
    const view = new DataView(buffer);

    const writeString = (offset: number, string: string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };

    writeString(0, 'RIFF');
    view.setUint32(4, 36 + totalLength * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, totalLength * 2, true);

    let offset = 44;
    for (const chunk of audioData) {
      for (let i = 0; i < chunk.length; i++) {
        const s = Math.max(-1, Math.min(1, chunk[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        offset += 2;
      }
    }
    return new Blob([buffer], { type: 'audio/wav' });
  };

  const generateSummary = async (transcription: { sender: 'user' | 'ai', text: string }[]) => {
    if (transcription.length === 0) return null;
    
    const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
    const prompt = `
      Siz professional tahlilchisiz. Quyidagi telefon muloqoti matni asosida chuqur tahlil o'tkazing.
      
      Muloqot matni:
      ${transcription.map(t => `${t.sender === 'user' ? 'Mijoz' : 'Operator'}: ${t.text}`).join('\n')}
    `;
    
    try {
      const response = await ai.models.generateContent({
        model: "gemini-3.1-pro-preview",
        contents: prompt,
        config: {
          responseMimeType: "application/json",
          responseSchema: {
            type: Type.OBJECT,
            properties: {
              summary: { type: Type.STRING, description: "Muloqotning qisqa va lo'nda xulosasi (o'zbek tilida)" },
              sentiment: { type: Type.STRING, enum: ["positive", "neutral", "negative"], description: "Mijozning umumiy kayfiyati" },
              actionItems: { 
                type: Type.ARRAY, 
                items: { type: Type.STRING },
                description: "Keyingi qadamlar yoki bajarilishi kerak bo'lgan vazifalar"
              },
              followUpDraft: { type: Type.STRING, description: "Mijozga yuborish uchun SMS yoki Telegram xabari loyihasi" }
            },
            required: ["summary", "sentiment", "actionItems", "followUpDraft"]
          }
        }
      });
      
      return JSON.parse(response.text);
    } catch (e) {
      console.error("Deep analysis error:", e);
      return null;
    }
  };

  const endCall = async () => {
    playSound.stopRing();
    const finalDuration = callDuration;
    const finalDialNumber = dialNumber;
    const finalLang = selectedLang.label;
    const finalTranscriptCount = transcriptionCount;
    const finalFullTranscription = [...fullTranscription];

    if (sessionRef.current) sessionRef.current.close?.();
    if (micStreamRef.current) micStreamRef.current.getTracks().forEach(t => t.stop());
    
    // Stop recording processor
    if (recordingProcessorRef.current) {
      recordingProcessorRef.current.disconnect();
      recordingProcessorRef.current = null;
    }

    sourcesRef.current.forEach(s => { try { s.stop(); } catch (e) {} });
    sourcesRef.current.clear();
    nextStartTimeRef.current = 0;
    setIsSpeaking(false);
    setUserSpeaking(false);
    setIsThinking(false);
    setIsOnHold(false);
    playSound.disconnect();
    setStatus(CallStatus.IDLE);
    setDialNumber('');
    setCallDuration(0);
    setTranscriptionCount(0);
    setFullTranscription([]);

    if (combinedAudioBufferRef.current.length > 0) {
      setIsProcessing(true);
      const id = Date.now().toString();
      
      // Create WAV blob from combined buffer (mixed mic + AI)
      const finalBlob = createWavBlob(combinedAudioBufferRef.current, 24000);
      await saveAudioBlob(id, finalBlob);
      
      const analysis = await generateSummary(finalFullTranscription);
      
      const newEntry: RecordedCall = {
        id,
        timestamp: new Date().toLocaleString(),
        duration: finalDuration,
        language: finalLang,
        transcriptionCount: finalTranscriptCount,
        fileName: `ZargarShop_${finalDialNumber || 'AI'}_${id}.wav`,
        summary: analysis?.summary || "Summary unavailable",
        sentiment: analysis?.sentiment,
        actionItems: analysis?.actionItems,
        followUpDraft: analysis?.followUpDraft,
        transcription: finalFullTranscription
      };
      
      const updatedHistory = [newEntry, ...recordings];
      setRecordings(updatedHistory);
      localStorage.setItem('call_history', JSON.stringify(updatedHistory));
      combinedAudioBufferRef.current = [];
      setIsProcessing(false);
    }
  };

  const startCall = async () => {
    if (!dialNumber && status === CallStatus.IDLE) return;
    setCallError(null);
    try {
      setStatus(CallStatus.CONNECTING);
      playSound.ring(); 
      combinedAudioBufferRef.current = [];
      
      const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
      
      try {
        audioContextInRef.current = new AudioContext({ sampleRate: 16000 });
        audioContextOutRef.current = new AudioContext({ sampleRate: 24000 });
        
        // Setup recording destination
        recordingDestRef.current = audioContextOutRef.current.createMediaStreamDestination();
        
        // Setup manual buffer capture for WAV
        recordingProcessorRef.current = audioContextOutRef.current.createScriptProcessor(4096, 1, 1);
        recordingProcessorRef.current.onaudioprocess = (e) => {
          if (statusRef.current === CallStatus.ACTIVE || statusRef.current === CallStatus.CONNECTING) {
            const inputData = e.inputBuffer.getChannelData(0);
            combinedAudioBufferRef.current.push(new Float32Array(inputData));
          }
        };
        recordingDestRef.current.connect(recordingProcessorRef.current);
        recordingProcessorRef.current.connect(audioContextOutRef.current.destination);
      } catch (err) {
        throw new Error("Audio tizimini ishga tushirib bo'lmadi. Iltimos, brauzeringizni tekshiring.");
      }

      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        micStreamRef.current = stream;
        
        // Connect mic to recording destination
        if (audioContextOutRef.current && recordingDestRef.current) {
          const micSource = audioContextOutRef.current.createMediaStreamSource(stream);
          micSource.connect(recordingDestRef.current);
        }
      } catch (err) {
        throw new Error("Mikrofonga ruxsat berilmadi. Iltimos, mikrofon sozlamalarini tekshiring.");
      }

      const sessionPromise = ai.live.connect({
        model: 'gemini-2.5-flash-native-audio-preview-09-2025',
        config: {
          responseModalities: [Modality.AUDIO],
          systemInstruction: `${selectedLang.instruction}\n\nVOCABULARY HINTS (Use these for better recognition): ${customVocabulary}`,
          speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: selectedVoice.id as any } } },
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
              const scriptProcessor = audioContextInRef.current!.createScriptProcessor(1024, 1, 1);
              scriptProcessor.onaudioprocess = (e) => {
                if (isOnHoldRef.current) return;
                const inputData = e.inputBuffer.getChannelData(0);
                const volume = Math.max(...inputData.map(Math.abs));
                const isUserSpeaking = volume > 0.04;
                
                if (isUserSpeaking) {
                  setUserSpeaking(true);
                  setIsThinking(false);
                  
                  // Barge-in: Stop AI speaking if user starts talking
                  if (isSpeaking) {
                    sourcesRef.current.forEach(s => { try { s.stop(); } catch (e) {} });
                    sourcesRef.current.clear();
                    nextStartTimeRef.current = audioContextOutRef.current?.currentTime || 0;
                    setIsSpeaking(false);
                  }
                } else {
                  setUserSpeaking(false);
                  if (status === CallStatus.ACTIVE && !isSpeaking) {
                    setIsThinking(true);
                  }
                }

                const int16 = new Int16Array(inputData.length);
                for (let i = 0; i < inputData.length; i++) int16[i] = inputData[i] * 32768;
                const pcmBlob = { data: encode(new Uint8Array(int16.buffer)), mimeType: 'audio/pcm;rate=16000' };
                sessionPromise.then(s => s.sendRealtimeInput({ media: pcmBlob })).catch(err => {
                  console.error("Input send error:", err);
                  setCallError("Ma'lumot yuborishda xatolik yuz berdi.");
                });
              };
              source.connect(scriptProcessor);
              scriptProcessor.connect(audioContextInRef.current!.destination);
            }, 300); 
          },
          onmessage: async (m: LiveServerMessage) => {
            if (m.serverContent?.outputTranscription) {
              const transcription = m.serverContent.outputTranscription;
              const text = typeof transcription === 'string' ? transcription : transcription.text;
              if (text) {
                setLastTranscription({ text, type: 'ai' });
                setFullTranscription(prev => [...prev, { sender: 'ai', text }]);
                setTranscriptionCount(prev => prev + 1);
              }
            }
            if (m.serverContent?.inputTranscription) {
              const transcription = m.serverContent.inputTranscription;
              const text = typeof transcription === 'string' ? transcription : transcription.text;
              if (text) {
                setLastTranscription({ text, type: 'user' });
                setFullTranscription(prev => [...prev, { sender: 'user', text }]);
              }
            }

            const audio = m.serverContent?.modelTurn?.parts[0]?.inlineData?.data;
            if (audio && audioContextOutRef.current && !isOnHoldRef.current) {
              const ctx = audioContextOutRef.current;
              nextStartTimeRef.current = Math.max(nextStartTimeRef.current, ctx.currentTime);
              try {
                const buffer = await decodeAudioData(decode(audio), ctx, 24000, 1);
                
                const src = ctx.createBufferSource();
                src.buffer = buffer;
                src.connect(ctx.destination);
                if (recordingDestRef.current) {
                  src.connect(recordingDestRef.current);
                }
                setIsSpeaking(true);
                setIsThinking(false);
                src.onended = () => {
                  sourcesRef.current.delete(src);
                  if (sourcesRef.current.size === 0) setIsSpeaking(false);
                };
                src.start(nextStartTimeRef.current);
                nextStartTimeRef.current += buffer.duration;
                sourcesRef.current.add(src);
              } catch (err) {
                console.error("Audio decode error:", err);
              }
            }
          },
          onerror: (err) => {
            console.error("Live session error:", err);
            setCallError("Aloqa uzildi. Iltimos, internetingizni tekshiring.");
            endCall();
          },
          onclose: () => endCall()
        }
      });
      sessionRef.current = await sessionPromise;
    } catch (e: any) { 
      console.error("Start call error:", e);
      setCallError(e.message || "Qo'ng'iroqni boshlab bo'lmadi.");
      endCall(); 
    }
  };

  const handleDownload = async (id: string, fileName: string) => {
    const blob = await getAudioBlob(id);
    if (blob) {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  const dialKeys = [
    { n: '1', l: ' ' }, { n: '2', l: 'A B C' }, { n: '3', l: 'D E F' },
    { n: '4', l: 'G H I' }, { n: '5', l: 'J K L' }, { n: '6', l: 'M N O' },
    { n: '7', l: 'P Q R S' }, { n: '8', l: 'T U V' }, { n: '9', l: 'W X Y Z' },
    { n: '*', l: ' ' }, { n: '0', l: '+' }, { n: '#' , l: ' '}
  ];

  return (
    <div className="fixed inset-0 bg-[#050914] text-white font-sans overflow-hidden flex items-center justify-center p-2 sm:p-4">
      <div className="relative w-full max-w-[320px] h-full max-h-[660px] bg-[#070b18] rounded-[48px] border-[1px] border-white/5 shadow-[0_0_80px_rgba(0,0,0,0.8)] overflow-hidden flex flex-col">
        
        {isProcessing && (
          <div className="absolute inset-0 z-[100] bg-black/80 backdrop-blur-md flex flex-col items-center justify-center p-8 text-center animate-in fade-in duration-500">
            <div className="w-16 h-16 mb-6 relative">
              <div className="absolute inset-0 border-4 border-[#34e0a1]/20 rounded-full"></div>
              <div className="absolute inset-0 border-4 border-t-[#34e0a1] rounded-full animate-spin"></div>
              <i className="fa-solid fa-wand-magic-sparkles absolute inset-0 flex items-center justify-center text-[#34e0a1] text-xl animate-pulse"></i>
            </div>
            <h3 className="text-sm font-black text-[#34e0a1] uppercase tracking-[0.2em] mb-2">Processing Call</h3>
            <p className="text-[10px] text-zinc-400 leading-relaxed">
              Gemini is analyzing your conversation to generate a concise summary and action items...
            </p>
          </div>
        )}

        {/* HEADER AREA */}
        <div className="pt-5 px-8 text-center shrink-0 z-10">
          <p className="text-[9px] font-bold tracking-[0.3em] opacity-60 uppercase mb-1">
            {currentTime.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
          </p>
          <h1 className="text-[52px] font-black leading-none mb-2">
            {currentTime.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: false })}
          </h1>
          
          <div className="flex justify-center space-x-6 text-[10px] font-bold opacity-60 mb-4">
            <span className={selectedLang.code === 'uz' ? 'text-white opacity-100 font-black' : ''}>U Z</span>
            <span className={selectedLang.code === 'ru' ? 'text-white opacity-100 font-black' : ''}>R U</span>
          </div>
        </div>

        {/* MAIN CONTENT AREA */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {activeTab === 'call' ? (
            status === CallStatus.IDLE ? (
              <div className="flex-1 flex flex-col z-10 px-7 overflow-hidden">
                <div className="text-center mb-4 h-6 flex items-center justify-center shrink-0">
                  {callError ? (
                    <div className="flex items-center space-x-2 text-red-400 bg-red-500/10 px-3 py-1 rounded-full border border-red-500/20 animate-in slide-in-from-top-2 duration-300">
                      <i className="fa-solid fa-triangle-exclamation text-[10px]"></i>
                      <span className="text-[9px] font-black uppercase tracking-wider">{callError}</span>
                    </div>
                  ) : (
                    <span className="text-lg font-light tracking-widest opacity-80">{dialNumber ? dialNumber : '+998'}</span>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-x-3 gap-y-3 mb-6 flex-1 items-center content-center">
                  {dialKeys.map(item => (
                    <button 
                      key={item.n} 
                      onClick={() => { 
                        playSound.keyPress(); 
                        setDialNumber(d => d + item.n); 
                        if (callError) setCallError(null);
                      }} 
                      className="w-[66px] h-[66px] rounded-full bg-[#131b31]/40 border border-white/5 flex flex-col items-center justify-center active:bg-[#1a2542] transition-all shadow-inner shadow-white/5 mx-auto"
                    >
                      <span className="text-[24px] font-medium leading-none mb-0.5">{item.n}</span>
                      <span className="text-[6px] font-black opacity-40 tracking-widest uppercase">{item.l}</span>
                    </button>
                  ))}
                </div>

                <div className="mb-6 flex items-center justify-between px-2 shrink-0">
                  <button onClick={() => setActiveTab('history')} className="w-11 h-11 rounded-full bg-[#131b31]/40 flex items-center justify-center border border-white/5">
                    <i className="fa-solid fa-clock-rotate-left text-xs text-white/40"></i>
                  </button>
                  
                  <button 
                    onClick={startCall}
                    className="w-[68px] h-[68px] bg-[#34e0a1] rounded-full flex items-center justify-center text-black text-2xl shadow-[0_0_30px_rgba(52,224,161,0.3)] active:scale-90 transition-all"
                  >
                    <i className="fa-solid fa-phone"></i>
                  </button>

                  <button 
                    onClick={() => {
                      setDialNumber(d => d.slice(0, -1));
                      if (callError) setCallError(null);
                    }}
                    className="w-11 h-11 rounded-full bg-[#131b31]/40 flex items-center justify-center border border-white/5 active:bg-white/10"
                  >
                    <i className="fa-solid fa-delete-left text-lg opacity-80"></i>
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col z-10 px-8 py-2 overflow-hidden relative bg-gradient-to-b from-transparent to-[#050914]/40">
                 {status === CallStatus.ACTIVE && (
                   <div className="absolute top-0 right-4 flex items-center space-x-1.5 bg-red-500/10 px-2 py-0.5 rounded-full border border-red-500/20">
                     <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.8)]"></div>
                     <span className="text-[7px] font-black text-red-500 tracking-[0.2em] uppercase">REC</span>
                   </div>
                 )}

                 <div className="text-center mt-3 shrink-0">
                   <h2 className="text-xl font-black mb-1 truncate">{dialNumber || 'Zargar Shop AI'}</h2>
                   <p className={`${isOnHold ? 'text-yellow-500' : 'text-[#34e0a1]'} font-bold text-[9px] tracking-widest uppercase`}>
                     {isOnHold ? 'On Hold' : status === CallStatus.CONNECTING ? 'Connecting...' : isThinking ? 'Thinking...' : formatDuration(callDuration)}
                   </p>
                 </div>

                 <div className="flex-1 flex flex-col items-center justify-center py-4 overflow-hidden relative">
                    {isSpeaking && (
                      <div className="absolute inset-0 flex items-center justify-center pointer-events-none overflow-hidden">
                        <div className="w-48 h-48 bg-[#34e0a1]/10 rounded-full blur-[60px] animate-pulse"></div>
                        <div className="absolute w-32 h-32 border border-[#34e0a1]/10 rounded-full animate-[ping_3s_linear_infinite]"></div>
                      </div>
                    )}
                    <div className="mb-6 h-8 flex items-center justify-center z-10">
                       {isOnHold ? (
                         <span className="text-[7px] font-black text-yellow-500 tracking-[0.3em] uppercase animate-pulse">Call On Hold</span>
                       ) : isSpeaking ? (
                         <div className="flex items-center space-x-2 bg-[#34e0a1] px-4 py-1.5 rounded-full shadow-[0_0_20px_rgba(52,224,161,0.4)] animate-in zoom-in duration-500">
                           <div className="flex space-x-1">
                             {[1, 2, 3].map(i => (
                               <div key={i} className="w-1 h-2 bg-black rounded-full animate-bounce" style={{ animationDelay: `${i * 0.1}s` }}></div>
                             ))}
                           </div>
                           <span className="text-[9px] font-black text-black tracking-[0.1em] uppercase">AI Speaking</span>
                         </div>
                       ) : userSpeaking ? (
                         <div className="flex items-center space-x-2 bg-blue-500/20 px-3 py-1 rounded-full border border-blue-500/30">
                           <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse"></div>
                           <span className="text-[7px] font-black text-blue-400 tracking-[0.3em] uppercase">User Speaking</span>
                         </div>
                       ) : (
                         <span className="text-[7px] font-black text-white/20 tracking-[0.3em] uppercase">Listening...</span>
                       )}
                    </div>

                    <div className="flex items-center space-x-2 mb-10 z-10">
                       {[...Array(16)].map((_, i) => (
                         <div 
                          key={i} 
                          className={`w-1.5 rounded-full transition-all duration-300 ${
                            isOnHold ? 'bg-zinc-700 opacity-50' :
                            isSpeaking ? 'bg-[#34e0a1] shadow-[0_0_15px_rgba(52,224,161,0.6)]' : 
                            userSpeaking ? 'bg-blue-400 shadow-[0_0_10px_rgba(96,165,250,0.4)]' : 
                            'bg-white/10'
                          } ${!isSpeaking && !userSpeaking && !isOnHold && status === CallStatus.ACTIVE ? 'animate-pulse' : ''}`}
                          style={{ 
                            height: isOnHold ? '4px' :
                                    isSpeaking ? `${20 + Math.random() * 60}px` : 
                                    userSpeaking ? `${15 + Math.random() * 40}px` : 
                                    '6px',
                            animationDelay: `${i * 0.05}s`
                          }}
                         ></div>
                       ))}
                    </div>

                    {lastTranscription && (
                      <div className="w-full px-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <div className={`p-3 rounded-2xl border ${lastTranscription.type === 'user' ? 'bg-blue-500/10 border-blue-500/20' : 'bg-[#34e0a1]/10 border-[#34e0a1]/20'}`}>
                          <p className={`text-[7px] font-black uppercase tracking-widest mb-1 ${lastTranscription.type === 'user' ? 'text-blue-400' : 'text-[#34e0a1]'}`}>
                            {lastTranscription.type === 'user' ? 'You' : 'AI'}
                          </p>
                          <p className="text-[11px] font-medium leading-relaxed italic line-clamp-3">"{lastTranscription.text}"</p>
                        </div>
                      </div>
                    )}
                 </div>

                 <div className="grid grid-cols-3 gap-y-6 mb-8 opacity-60 shrink-0">
                    {[
                      { i: 'microphone-slash', t: 'MUTE' }, { i: 'table-cells', t: 'KEYPAD' }, { i: 'volume-high', t: 'SPEAKER' },
                      { i: 'plus', t: 'ADD' }, { i: 'video', t: 'VIDEO' }, { i: 'user', t: 'CONTACTS' }
                    ].map((item, idx) => (
                      <div key={idx} className="flex flex-col items-center">
                        <div className="w-11 h-11 rounded-full bg-white/5 flex items-center justify-center mb-1 border border-white/5">
                           <i className={`fa-solid fa-${item.i} text-xs`}></i>
                        </div>
                        <span className="text-[5px] font-black tracking-widest">{item.t}</span>
                      </div>
                    ))}
                 </div>

                 <div className="flex justify-center items-center space-x-8 mb-8 shrink-0">
                    <button 
                      onClick={() => setIsOnHold(!isOnHold)}
                      className={`w-14 h-14 rounded-full flex items-center justify-center text-xl transition-all ${isOnHold ? 'bg-yellow-500 text-white shadow-[0_0_20px_rgba(234,179,8,0.3)]' : 'bg-white/10 text-white hover:bg-white/20'}`}
                    >
                      <i className={`fa-solid fa-${isOnHold ? 'play' : 'pause'}`}></i>
                    </button>
                    <button 
                      onClick={endCall}
                      className="w-16 h-16 bg-red-500 rounded-full flex items-center justify-center text-white text-2xl shadow-[0_0_30px_rgba(239,68,68,0.3)] active:scale-90 transition-all"
                    >
                      <i className="fa-solid fa-phone-slash"></i>
                    </button>
                 </div>
              </div>
            )
          ) : activeTab === 'history' ? (
            <div className="flex-1 flex flex-col z-10 px-6 overflow-hidden">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-black tracking-widest text-[#34e0a1] uppercase">Call History</h2>
                <button onClick={() => setActiveTab('call')} className="text-zinc-500 hover:text-white transition-all">
                  <i className="fa-solid fa-xmark"></i>
                </button>
              </div>
              
              <div className="mb-4">
                <div className="relative">
                  <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600 text-[10px]"></i>
                  <input 
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Qidirish (masalan: 'yetkazib berish')..."
                    className="w-full bg-white/5 border border-white/5 rounded-xl py-2 pl-9 pr-4 text-[10px] focus:outline-none focus:border-[#34e0a1]/30 transition-all text-white placeholder:text-zinc-600"
                  />
                </div>
              </div>
              
              <div className="flex-1 overflow-y-auto space-y-3 pb-6 pr-1 custom-scrollbar">
                {recordings.filter(r => 
                  r.summary?.toLowerCase().includes(searchQuery.toLowerCase()) || 
                  r.fileName.toLowerCase().includes(searchQuery.toLowerCase()) ||
                  r.transcription?.some(t => t.text.toLowerCase().includes(searchQuery.toLowerCase()))
                ).length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full opacity-20 text-center">
                    <i className="fa-solid fa-clock-rotate-left text-4xl mb-3"></i>
                    <p className="text-[10px] font-bold uppercase tracking-widest">No recordings found</p>
                  </div>
                ) : (
                  recordings
                    .filter(r => 
                      r.summary?.toLowerCase().includes(searchQuery.toLowerCase()) || 
                      r.fileName.toLowerCase().includes(searchQuery.toLowerCase()) ||
                      r.transcription?.some(t => t.text.toLowerCase().includes(searchQuery.toLowerCase()))
                    )
                    .map((rec) => (
                    <div key={rec.id} className="bg-[#131b31]/40 border border-white/5 rounded-2xl p-4 transition-all hover:bg-[#1a2542]">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <p className="text-[10px] font-black text-[#34e0a1] mb-0.5">{rec.timestamp}</p>
                          <p className="text-xs font-bold truncate max-w-[120px]">{rec.fileName}</p>
                        </div>
                        <div className="flex space-x-2">
                          <button 
                            onClick={() => handleDownload(rec.id, rec.fileName)}
                            className="w-8 h-8 rounded-full bg-[#34e0a1]/10 text-[#34e0a1] flex items-center justify-center hover:bg-[#34e0a1] hover:text-black transition-all"
                            title="Download"
                          >
                            <i className="fa-solid fa-download text-xs"></i>
                          </button>
                          <button 
                            onClick={async () => {
                              if (confirm('Ushbu yozuvni o\'chirib tashlamoqchimisiz?')) {
                                await deleteAudioBlob(rec.id);
                                const updated = recordings.filter(r => r.id !== rec.id);
                                setRecordings(updated);
                                localStorage.setItem('call_history', JSON.stringify(updated));
                              }
                            }}
                            className="w-8 h-8 rounded-full bg-red-500/10 text-red-500 flex items-center justify-center hover:bg-red-500 hover:text-white transition-all"
                            title="Delete"
                          >
                            <i className="fa-solid fa-trash-can text-xs"></i>
                          </button>
                        </div>
                      </div>
                      <div className="flex items-center space-x-3 text-[8px] font-black uppercase tracking-widest">
                        <span className="opacity-40"><i className="fa-solid fa-clock mr-1"></i> {formatDuration(rec.duration)}</span>
                        <span className="opacity-40"><i className="fa-solid fa-globe mr-1"></i> {rec.language}</span>
                        {rec.sentiment && (
                          <span className={`px-2 py-0.5 rounded-full border ${
                            rec.sentiment === 'positive' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' :
                            rec.sentiment === 'negative' ? 'bg-red-500/10 border-red-500/30 text-red-400' :
                            'bg-blue-500/10 border-blue-500/30 text-blue-400'
                          }`}>
                            {rec.sentiment}
                          </span>
                        )}
                      </div>

                      {rec.summary && (
                        <div className="mt-3 p-3 bg-white/5 rounded-xl border border-white/5">
                          <p className="text-[8px] font-black text-[#34e0a1] uppercase tracking-widest mb-2 flex items-center">
                            <i className="fa-solid fa-wand-magic-sparkles mr-1.5"></i>
                            AI Insights
                          </p>
                          <div className="text-[10px] leading-relaxed text-zinc-300 whitespace-pre-wrap italic mb-3">
                            {rec.summary}
                          </div>
                          
                          {rec.actionItems && rec.actionItems.length > 0 && (
                            <div className="mb-3">
                              <p className="text-[7px] font-black text-white/40 uppercase mb-1.5">Action Items</p>
                              <ul className="space-y-1">
                                {rec.actionItems.map((item, idx) => (
                                  <li key={idx} className="text-[9px] text-zinc-400 flex items-start">
                                    <span className="text-[#34e0a1] mr-1.5">•</span>
                                    {item}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {rec.followUpDraft && (
                            <div className="bg-black/30 rounded-lg p-2 border border-white/5">
                              <div className="flex justify-between items-center mb-1.5">
                                <p className="text-[7px] font-black text-white/40 uppercase">Follow-up Draft</p>
                                <button 
                                  onClick={() => {
                                    navigator.clipboard.writeText(rec.followUpDraft || '');
                                    alert('Xabar nusxalandi!');
                                  }}
                                  className="text-[7px] text-[#34e0a1] hover:underline"
                                >
                                  Copy
                                </button>
                              </div>
                              <p className="text-[9px] text-zinc-500 italic leading-snug">"{rec.followUpDraft}"</p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col z-10 px-6 overflow-hidden">
               <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-black tracking-widest text-[#34e0a1] uppercase">Settings</h2>
                <button onClick={() => setActiveTab('call')} className="text-zinc-500 hover:text-white transition-all">
                  <i className="fa-solid fa-xmark"></i>
                </button>
              </div>
               <div className="space-y-3 overflow-y-auto pb-6 custom-scrollbar">
                 <div className="bg-white/5 border border-white/5 rounded-xl p-4">
                   <p className="text-[8px] font-black text-[#34e0a1] uppercase tracking-[0.2em] mb-3">AI Voice Selection</p>
                   <div className="grid grid-cols-1 gap-2">
                     {VOICES.map(v => (
                       <button 
                         key={v.id} 
                         onClick={() => setSelectedVoice(v)}
                         className={`flex items-center justify-between p-3 rounded-xl border transition-all ${selectedVoice.id === v.id ? 'bg-[#34e0a1]/10 border-[#34e0a1]/30' : 'bg-black/20 border-white/5 text-zinc-500'}`}
                       >
                         <div className="text-left">
                           <p className={`text-[10px] font-bold uppercase tracking-widest ${selectedVoice.id === v.id ? 'text-white' : 'text-zinc-500'}`}>{v.name}</p>
                           <p className="text-[8px] opacity-60">{v.description}</p>
                         </div>
                         <div className="flex items-center space-x-2">
                           <span className="text-[7px] px-1.5 py-0.5 rounded bg-white/5 border border-white/10 uppercase font-black">{v.gender}</span>
                           {selectedVoice.id === v.id && <i className="fa-solid fa-circle-check text-[#34e0a1] text-[10px]"></i>}
                         </div>
                       </button>
                     ))}
                   </div>
                 </div>

                 <div className="bg-white/5 border border-white/5 rounded-xl p-4">
                   <p className="text-[8px] font-black text-[#34e0a1] uppercase tracking-[0.2em] mb-3">Language Selection</p>
                   <div className="grid grid-cols-2 gap-2">
                    {LANGUAGES.map(l => (
                      <button key={l.code} onClick={() => setSelectedLang(l)} className={`flex items-center justify-between p-3 rounded-xl border transition-all ${selectedLang.code === l.code ? 'bg-[#34e0a1]/10 border-[#34e0a1]/30' : 'bg-black/20 border-white/5 text-zinc-500'}`}>
                        <div className="flex items-center space-x-2">
                          <span className="text-xs">{l.flag}</span>
                          <span className="font-bold text-[9px] uppercase tracking-widest">{l.label}</span>
                        </div>
                        {selectedLang.code === l.code && <i className="fa-solid fa-check text-[#34e0a1] text-[8px]"></i>}
                      </button>
                    ))}
                   </div>
                 </div>

                 <div className="bg-white/5 border border-white/5 rounded-xl p-4">
                   <p className="text-[8px] font-black text-[#34e0a1] uppercase tracking-[0.2em] mb-3">Custom Vocabulary (Fine-tuning)</p>
                   <textarea 
                     value={customVocabulary}
                     onChange={(e) => setCustomVocabulary(e.target.value)}
                     className="w-full bg-black/20 border border-white/10 rounded-lg p-2 text-[10px] font-medium focus:outline-none focus:border-[#34e0a1]/50 transition-all min-h-[80px] resize-none text-white"
                     placeholder="Enter keywords separated by commas..."
                   />
                   <p className="text-[7px] opacity-40 mt-2 leading-relaxed">Add specific product names, locations, or technical terms to improve recognition accuracy.</p>
                 </div>
               </div>
            </div>
          )}
        </div>

        {/* NEW BOTTOM NAVIGATION (TAB BAR) */}
        {status === CallStatus.IDLE && (
          <div className="h-16 bg-[#070b18] border-t border-white/5 flex items-center justify-around px-8 shrink-0 z-20">
            <button 
              onClick={() => setActiveTab('call')} 
              className={`flex flex-col items-center space-y-1 transition-all ${activeTab === 'call' ? 'text-[#34e0a1]' : 'text-zinc-600 hover:text-zinc-400'}`}
            >
              <i className="fa-solid fa-phone text-lg"></i>
              <span className="text-[6px] font-black tracking-widest uppercase">Phone</span>
            </button>
            <button 
              onClick={() => setActiveTab('history')} 
              className={`flex flex-col items-center space-y-1 transition-all ${activeTab === 'history' ? 'text-[#34e0a1]' : 'text-zinc-600 hover:text-zinc-400'}`}
            >
              <i className="fa-solid fa-clock-rotate-left text-lg"></i>
              <span className="text-[6px] font-black tracking-widest uppercase">History</span>
            </button>
            <button 
              onClick={() => setActiveTab('settings')} 
              className={`flex flex-col items-center space-y-1 transition-all ${activeTab === 'settings' ? 'text-[#34e0a1]' : 'text-zinc-600 hover:text-zinc-400'}`}
            >
              <i className="fa-solid fa-gear text-lg"></i>
              <span className="text-[6px] font-black tracking-widest uppercase">Settings</span>
            </button>
          </div>
        )}

        {/* HOME INDICATOR */}
        <div className="h-6 flex items-center justify-center shrink-0">
          <div className="w-24 h-1 bg-white/10 rounded-full"></div>
        </div>
      </div>
      
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(52, 224, 161, 0.2);
          border-radius: 10px;
        }
        @keyframes breathe {
          0%, 100% { height: 4px; opacity: 0.2; }
          50% { height: 8px; opacity: 0.4; }
        }
        .animate-breathe {
          animation: breathe 2s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
};

export default App;
