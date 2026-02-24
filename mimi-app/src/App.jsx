import React, { useState, useEffect, useRef } from 'react';
import { Send, User, Mic, Image as ImageIcon, X, Sparkles, Volume2, VolumeX } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Confetti from 'react-confetti';
import { useWindowSize } from 'react-use';

const API_BASE = '/api';

const SMART_CHIPS = [
    "🚀 Lực hấp dẫn hoạt động như thế nào hả chị?",
    "🚲 Tại sao phanh xe đạp lại tạo ra lực ma sát?",
    "🫁 Phổi giúp chúng ta thở như thế nào ạ?",
    "🩸 Máu chảy trong cơ thể mình ra sao chị nhỉ?",
    "🍃 Tại sao thực vật lại quan trọng trong chuỗi thức ăn?"
];

const POSITIVE_KEYWORDS = ["giỏi quá", "xuất sắc", "đúng rồi", "chính xác", "tuyệt vời", "rất tốt", "hô hô", "chúc mừng"];

const BouncingHeartsLoader = () => (
    <div className="bouncing-hearts">
        <span className="heart" style={{ animationDelay: '0s' }}>💖</span>
        <span className="heart" style={{ animationDelay: '0.2s' }}>💖</span>
        <span className="heart" style={{ animationDelay: '0.4s' }}>💖</span>
        <span className="loading-text">Chị đang suy nghĩ...</span>
    </div>
);

const MimiChat = () => {
    const [messages, setMessages] = useState([
        { role: 'bot', content: 'Chào Mimi! Chị đã sẵn sàng hỗ trợ em học tập rồi đây. Hôm nay em muốn cùng chị khám phá chủ đề nào nào? ✨' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [selectedImage, setSelectedImage] = useState(null);
    const [isRecording, setIsRecording] = useState(false);
    const [showConfetti, setShowConfetti] = useState(false);
    const [speakingIndex, setSpeakingIndex] = useState(null);

    const scrollRef = useRef(null);
    const fileInputRef = useRef(null);
    const recognitionRef = useRef(null);
    const { width, height } = useWindowSize();

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, loading]);

    useEffect(() => {
        if ('webkitSpeechRecognition' in window) {
            const SpeechRecognition = window.webkitSpeechRecognition;
            recognitionRef.current = new SpeechRecognition();
            recognitionRef.current.continuous = false;
            recognitionRef.current.interimResults = false;
            recognitionRef.current.lang = 'vi-VN';

            recognitionRef.current.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                setInput((prev) => prev + (prev ? ' ' : '') + transcript);
                setIsRecording(false);
            };

            recognitionRef.current.onerror = (event) => {
                console.error('Speech recognition error', event.error);
                setIsRecording(false);
            };

            recognitionRef.current.onend = () => {
                setIsRecording(false);
            };
        }
    }, []);

    const toggleRecording = () => {
        if (isRecording) {
            recognitionRef.current?.stop();
            setIsRecording(false);
        } else {
            setInput('');
            recognitionRef.current?.start();
            setIsRecording(true);
        }
    };

    const handleImageSelect = (e) => {
        if (e.target.files && e.target.files[0]) {
            setSelectedImage(e.target.files[0]);
        }
    };

    const removeImage = () => {
        setSelectedImage(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const handleSpeak = (text, index) => {
        if (speakingIndex === index) {
            window.speechSynthesis.cancel();
            setSpeakingIndex(null);
            return;
        }
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);

        // Find best Vietnamese voice
        const voices = window.speechSynthesis.getVoices();
        const viVoice = voices.find(v => v.lang === 'vi-VN' && v.name.includes('Google')) ||
            voices.find(v => v.lang === 'vi-VN') ||
            voices.find(v => v.lang.startsWith('vi'));

        if (viVoice) {
            utterance.voice = viVoice;
        }

        utterance.lang = 'vi-VN';
        utterance.rate = 0.9; // Slightly slower for better clarity
        utterance.pitch = 1.0;

        utterance.onend = () => setSpeakingIndex(null);
        utterance.onerror = () => setSpeakingIndex(null);

        setSpeakingIndex(index);
        window.speechSynthesis.speak(utterance);
    };

    const checkAndTriggerConfetti = (text) => {
        const lowerText = text.toLowerCase();
        if (POSITIVE_KEYWORDS.some(kw => lowerText.includes(kw))) {
            setShowConfetti(true);
            setTimeout(() => setShowConfetti(false), 5000);
        }
    };

    const handleSend = async (customInput = null) => {
        const currentInput = customInput || input;
        if ((!currentInput.trim() && !selectedImage) || loading) return;

        const userMsg = currentInput.trim();
        const hasImage = !!selectedImage;
        const currentImage = selectedImage;

        setInput('');
        setSelectedImage(null);
        if (fileInputRef.current) fileInputRef.current.value = '';

        setMessages(prev => [...prev, {
            role: 'user',
            content: userMsg || '(Đã gửi một ảnh)',
            image: currentImage ? URL.createObjectURL(currentImage) : null
        }]);
        setLoading(true);
        setShowConfetti(false);
        window.speechSynthesis.cancel();
        setSpeakingIndex(null);

        try {
            let data;
            if (hasImage) {
                const formData = new FormData();
                formData.append('message', userMsg);
                formData.append('user_id', 'mimi_user');
                formData.append('file', currentImage);

                const res = await fetch(`${API_BASE}/mimi/chat/multimodal`, {
                    method: 'POST',
                    body: formData
                });
                data = await res.json();
            } else {
                const res = await fetch(`${API_BASE}/mimi/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: userMsg, user_id: 'mimi_user' })
                });
                data = await res.json();
            }
            const botResponse = data.response;
            setMessages(prev => [...prev, { role: 'bot', content: botResponse }]);
            checkAndTriggerConfetti(botResponse);
        } catch (err) {
            console.error(err);
            setMessages(prev => [...prev, { role: 'bot', content: 'Ối, có lỗi gì đó rồi. Em thử lại xem sao nhé!' }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="chat-container">
            {showConfetti && <Confetti width={width} height={height} numberOfPieces={300} recycle={false} />}

            <div className="messages" ref={scrollRef}>
                <AnimatePresence>
                    {messages.map((msg, i) => (
                        <motion.div
                            key={i}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={`message ${msg.role}`}
                        >
                            <div className="avatar">
                                {msg.role === 'user' ? <User size={20} /> : <Sparkles size={20} />}
                            </div>
                            <div className="content">
                                {msg.image && (
                                    <img src={msg.image} alt="Upload" style={{ maxWidth: '100%', borderRadius: '0.5rem', marginBottom: '0.5rem' }} />
                                )}
                                {msg.role === 'bot' ? (
                                    <div className="markdown-content">
                                        <Markdown remarkPlugins={[remarkGfm]}>
                                            {msg.content}
                                        </Markdown>
                                    </div>
                                ) : (
                                    <div>{msg.content}</div>
                                )}
                                {msg.role === 'bot' && (
                                    <button
                                        className="tts-btn"
                                        onClick={() => handleSpeak(msg.content, i)}
                                        title="Đọc câu trả lời"
                                    >
                                        {speakingIndex === i ? <VolumeX size={16} /> : <Volume2 size={16} />}
                                    </button>
                                )}
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>
                {loading && <BouncingHeartsLoader />}
            </div>

            <div className="input-outer-container">
                <div className="smart-chips-wrapper">
                    {SMART_CHIPS.map((chip, idx) => (
                        <button key={idx} className="smart-chip" onClick={() => handleSend(chip)}>
                            {chip}
                        </button>
                    ))}
                </div>

                <div className="input-container">
                    {selectedImage && (
                        <div className="image-preview">
                            <img src={URL.createObjectURL(selectedImage)} alt="Preview" />
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{selectedImage.name}</span>
                            <button onClick={removeImage}><X size={16} /></button>
                        </div>
                    )}

                    <div className="input-area">
                        <input type="file" ref={fileInputRef} onChange={handleImageSelect} accept="image/*" style={{ display: 'none' }} />

                        <button className="action-btn" onClick={() => fileInputRef.current?.click()} title="Tải ảnh lên">
                            <ImageIcon size={20} />
                        </button>

                        <button className={`action-btn ${isRecording ? 'recording' : ''}`} onClick={toggleRecording} title={isRecording ? "Đang nghe..." : "Nhấn để nói"}>
                            <Mic size={20} />
                        </button>

                        <input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            placeholder={isRecording ? "Chị đang nghe em nói nè..." : "Hãy hỏi chị bất cứ điều gì nha..."}
                        />

                        <button className="send-btn" onClick={() => handleSend()} disabled={loading || (!input.trim() && !selectedImage)}>
                            <Send size={18} /> Gửi
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

function App() {
    return (
        <div className="app">
            <nav className="navbar">
                <div className="logo" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Sparkles size={24} color="#fef08a" style={{ fill: '#fef08a' }} />
                    Mimi Home Tutor 🌸
                </div>
            </nav>
            <main>
                <MimiChat />
            </main>
        </div>
    );
}

export default App;
