import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

app = FastAPI()

# Gemini API klientini ishga tushiramiz (GEMINI_API_KEY muhit o'zgaruvchisidan olinadi)
client = genai.Client()

# App.tsx dagi Zargar Shop operatori prompti
ZARGARSHOP_PROMPT = """
Sening isming: Zargar Shop AI Operatori.
Sening vazifang: "Zargar Shop" telemagazini va onlayn-do'koni mijozlariga xizmat ko'rsatish.

MULOQOT USLUBI VA INSONIYLIK (O'TA MUHIM):
- Sen shunchaki robot emassan, sen samimiy, jonli va yordamga tayyor insonga o'xshash operator bo'lishing kerak.
- Gaplaringda tabiiy to'xtalishlar, "hmm", "tushunarli", "ha, albatta", "shunaqa deng", "ha-ya", "albatta-da" kabi so'zlardan o'rinli foydalanib, muloqotni jonli qil.
- Gapni juda rasmiy boshlama. O'zbekona mehmondostlik va samimiylik bilan gaplash.
- Mijoz gapirayotganda diqqat bilan tingla. Agar mijoz seni bo'lsa, darhol to'xta va uni tingla (Barge-in).
- Ovoz ohanging iliq, xushmuomala va ishonarli bo'lsin. Xuddi yaqin do'sting bilan gaplashayotgandek samimiy bo'l.
- Mijozning kayfiyatiga qarab moslash.
- Qisqa javoblar berishga harakat qil, monolog o'qima. Mijoz bilan doimiy muloqotda bo'l.

QUYIDAGI QOIDALAR VA MA'LUMOTLAR ASOSIDA JAVOB BER:
1. SALOMLASHUV: "Assalomu alaykum! Siz bilan “Zargar Shop” bog‘lanmoqda. Qanday mahsulot sizga qiziq?"
2. BUYURTMA: Har doim LOT RAQAMINI so'ra.
3. LOT RAQAMI AYTILSA: Maqtov aytib, ma'lumotlarini so'ra.
4. YETKAZIB BERISH: Toshkent shahriga 39 000 so'm, Viloyatlarga 49 000 so'm.
5. DO'KON: Faqat onlayn yetkazib berish.
6. SIFAT: 585 probali oltin suvi qoplangan.
7. TO'LOV: Eshik tagida.
"""

# Gemini sozlamalari (Faqat Audio qaytarish)
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    system_instruction=types.Content(parts=[types.Part.from_text(text=ZARGARSHOP_PROMPT)]),
)

@app.websocket("/ws/asterisk")
async def asterisk_websocket(websocket: WebSocket):
    await websocket.accept()
    print("📞 Asterisk ulandi! Yangi qo'ng'iroq...")
    
    try:
        # Gemini 2.5 flash modeli bilan Live API ulanishi
        async with client.aio.live.connect(model="gemini-2.5-flash", config=config) as session:
            
            # 1. Asteriskdan keladigan mijoz ovozini Gemini'ga uzatish
            async def receive_from_asterisk():
                try:
                    while True:
                        audio_data = await websocket.receive_bytes()
                        await session.send(
                            input=types.LiveClientRealtimeInput(
                                media_chunks=[
                                    types.Blob(
                                        mime_type="audio/pcm;rate=16000",
                                        data=audio_data
                                    )
                                ]
                            )
                        )
                except WebSocketDisconnect:
                    print("📴 Asterisk aloqani uzdi (Mijoz go'shakni qo'ydi).")

            # 2. Gemini o'ylab topgan javob (audio)ni Asteriskga uzatish
            async def receive_from_gemini():
                try:
                    async for response in session.receive():
                        server_content = response.server_content
                        if server_content is not None:
                            model_turn = server_content.model_turn
                            if model_turn:
                                for part in model_turn.parts:
                                    if part.inline_data and part.inline_data.data:
                                        await websocket.send_bytes(part.inline_data.data)
                except Exception as e:
                    print(f"Gemini error: {e}")

            # Ikkala jarayonni parallel ishga tushirish
            await asyncio.gather(
                receive_from_asterisk(),
                receive_from_gemini()
            )

    except Exception as e:
        print(f"❌ Xatolik yuz berdi: {e}")
    finally:
        print("✅ Suhbat yakunlandi. CRM logikasi shu yerda ishlaydi.")

if __name__ == "__main__":
    import uvicorn
    print("🚀 FastAPI server ishga tushmoqda...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
