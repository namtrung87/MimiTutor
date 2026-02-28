import React, { useState, useEffect, useRef } from 'react';
import { Send, User, Mic, Image as ImageIcon, X, Sparkles, Volume2, VolumeX, ThumbsUp, ThumbsDown, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Confetti from 'react-confetti';
import { useWindowSize } from 'react-use';

// Typewriter Component for Simulated Streaming
const Typewriter = ({ text, delay = 20, onComplete }) => {
    const [currentText, setCurrentText] = useState('');
    const [currentIndex, setCurrentIndex] = useState(0);

    useEffect(() => {
        if (currentIndex < text.length) {
            const timeout = setTimeout(() => {
                setCurrentText(prevText => prevText + text[currentIndex]);
                setCurrentIndex(prevIndex => prevIndex + 1);
            }, delay);
            return () => clearTimeout(timeout);
        } else if (onComplete) {
            onComplete();
        }
    }, [currentIndex, delay, text]);

    return (
        <div className="markdown-content">
            <Markdown remarkPlugins={[remarkGfm]}>
                {currentText}
            </Markdown>
        </div>
    );
};


const getApiBase = () => {
    const { hostname, protocol } = window.location;
    // If we're on a LAN IP or specific host, point to the backend on port 8000
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
        return `${protocol}//${hostname}:8000`;
    }
    return import.meta.env.VITE_API_URL || '/api';
};

const API_BASE = getApiBase();
console.log('Mimi API Base:', API_BASE);

// Đã gỡ bỏ Smart Chips theo yêu cầu

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
    const [messages, setMessages] = useState(() => {
        const saved = localStorage.getItem('mimi_messages');
        if (saved) {
            // Clean up streaming state on load
            return JSON.parse(saved).map(m => ({ ...m, isStreaming: false }));
        }
        return [{ role: 'bot', content: 'Chào Mimi! Chị đã sẵn sàng hỗ trợ em học tập rồi đây. Hôm nay em muốn cùng chị khám phá chủ đề nào nào? ✨', rating: null, isStreaming: false }];
    });
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [selectedImage, setSelectedImage] = useState(null);
    const [isRecording, setIsRecording] = useState(false);
    const [showConfetti, setShowConfetti] = useState(false);
    const [speakingIndex, setSpeakingIndex] = useState(null);
    // Persistent Session ID generator
    const [sessionId] = useState(() => {
        const saved = localStorage.getItem('mimi_session_id');
        if (saved) return saved;
        return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    });

    useEffect(() => {
        localStorage.setItem('mimi_messages', JSON.stringify(messages));
        localStorage.setItem('mimi_session_id', sessionId);
    }, [messages, sessionId]);


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

        // Ưu tiên tìm giọng nữ tiếng Việt (ví dụ: Google, Hoài My), tránh giọng nam (Ví dụ: Microsoft An)
        const voices = window.speechSynthesis.getVoices();
        const viVoice = voices.find(v => v.lang === 'vi-VN' && (v.name.includes('Hoài My') || v.name.includes('HoaiMy'))) ||
            voices.find(v => v.lang === 'vi-VN' && v.name.includes('Female')) ||
            voices.find(v => v.lang === 'vi-VN' && v.name.includes('Google')) ||
            voices.find(v => v.lang === 'vi-VN' && !v.name.toLowerCase().includes('an')) ||
            voices.find(v => v.lang === 'vi-VN');

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

    const handleFeedback = async (index, rating) => {
        setMessages(prev => prev.map((msg, i) => i === index ? { ...msg, rating } : msg));
        try {
            await fetch(`${API_BASE}/mimi/feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId, message_index: index, rating })
            });
        } catch (err) {
            console.error("Feedback error", err);
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
                formData.append('session_id', sessionId);
                formData.append('file', currentImage);

                const res = await fetch(`${API_BASE}/mimi/chat/multimodal`, {
                    method: 'POST',
                    body: formData
                });
                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                data = await res.json();
            } else {
                const res = await fetch(`${API_BASE}/mimi/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: userMsg, user_id: 'mimi_user', session_id: sessionId })
                });
                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                data = await res.json();
            }
            const botResponse = data.response;
            setMessages(prev => [...prev, { role: 'bot', content: botResponse, rating: null, isStreaming: true }]);
            // Note: Confetti will trigger after streaming completes, handled in component render or could trigger immediately
            // For simplicity, trigger immediately as response arrives
            checkAndTriggerConfetti(botResponse);
        } catch (err) {
            console.error("Mimi API Error:", err);

            if (err.message.includes('429')) {
                // Rate limit — no retry, just inform
                setMessages(prev => [...prev, {
                    role: 'bot',
                    content: 'Bạn hỏi hơi nhanh rồi đó! Nghỉ tay 1 phút rồi quay lại nha Mimi! 🌸',
                    rating: null, isStreaming: false
                }]);
            } else {
                // True network error: attempt one silent auto-retry after 2s
                let retrySucceeded = false;
                try {
                    await new Promise(r => setTimeout(r, 2000));
                    const retryRes = await fetch(`${API_BASE}/mimi/chat`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: userMsg, user_id: 'mimi_user', session_id: sessionId })
                    });
                    if (!retryRes.ok) throw new Error(`Retry failed: ${retryRes.status}`);
                    const retryData = await retryRes.json();
                    setMessages(prev => [...prev, { role: 'bot', content: retryData.response, rating: null, isStreaming: true }]);
                    checkAndTriggerConfetti(retryData.response);
                    retrySucceeded = true;
                } catch (retryErr) {
                    console.error("Mimi: auto-retry also failed", retryErr);
                }

                if (!retrySucceeded) {
                    // Both original and retry failed — show error with manual retry button
                    setMessages(prev => [...prev, {
                        role: 'bot',
                        content: 'Ối, kết nối với "não" của chị bị gián đoạn. Chị em mình thử lại nhé! ✨',
                        rating: null, isStreaming: false,
                        isError: true, retryInput: userMsg
                    }]);
                }
            }
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
                                    <>
                                        {msg.isStreaming ? (
                                            <Typewriter
                                                text={msg.content}
                                                onComplete={() => {
                                                    setMessages(prev => prev.map((m, idx) => idx === i ? { ...m, isStreaming: false } : m));
                                                }}
                                            />
                                        ) : (
                                            <div className="markdown-content">
                                                <Markdown remarkPlugins={[remarkGfm]}>
                                                    {msg.content}
                                                </Markdown>
                                            </div>
                                        )}
                                        <div className="message-actions" style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                                            <button
                                                className="tts-btn"
                                                onClick={() => handleSpeak(msg.content, i)}
                                                title="Đọc câu trả lời"
                                                style={{ background: 'none', border: 'none', cursor: 'pointer', color: speakingIndex === i ? 'var(--primary-color)' : 'var(--text-muted)' }}
                                            >
                                                {speakingIndex === i ? <VolumeX size={16} /> : <Volume2 size={16} />}
                                            </button>
                                            {!msg.isStreaming && i > 0 && (
                                                <>
                                                    <button onClick={() => handleFeedback(i, 1)} title="Thích câu trả lời!" style={{ background: 'none', border: 'none', cursor: 'pointer', color: msg.rating === 1 ? '#22c55e' : 'var(--text-muted)' }}>
                                                        <ThumbsUp size={16} />
                                                    </button>
                                                    <button onClick={() => handleFeedback(i, -1)} title="Câu trả lời chưa tốt" style={{ background: 'none', border: 'none', cursor: 'pointer', color: msg.rating === -1 ? '#ef4444' : 'var(--text-muted)' }}>
                                                        <ThumbsDown size={16} />
                                                    </button>
                                                </>
                                            )}
                                            {msg.isError && msg.retryInput && (
                                                <button
                                                    onClick={() => handleSend(msg.retryInput)}
                                                    title="Gửi lại câu hỏi"
                                                    style={{ background: 'none', border: '1px solid var(--primary-color)', borderRadius: '12px', padding: '2px 10px', fontSize: '0.75rem', cursor: 'pointer', color: 'var(--primary-color)' }}
                                                >
                                                    Thử lại 🔄
                                                </button>
                                            )}
                                        </div>
                                    </>
                                ) : (
                                    <div>{msg.content}</div>
                                )}
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>
                {loading && <BouncingHeartsLoader />}
            </div>

            <div className="input-outer-container">
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
            <nav className="navbar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div className="logo" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Sparkles size={24} color="#fef08a" style={{ fill: '#fef08a' }} />
                    Mimi Home Tutor 🌸
                </div>
                <button
                    onClick={() => {
                        if (window.confirm('Em có chắc muốn xóa toàn bộ cuộc trò chuyện không?')) {
                            localStorage.removeItem('mimi_messages');
                            localStorage.removeItem('mimi_session_id');
                            window.location.reload();
                        }
                    }}
                    style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '8px', zIndex: 100 }}
                    title="Xóa trò chuyện"
                >
                    <Trash2 size={20} />
                </button>
            </nav>
            <main>
                <MimiChat />
            </main>
        </div>
    );
}

export default App;
