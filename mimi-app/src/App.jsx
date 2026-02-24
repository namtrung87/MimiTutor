import React, { useState, useEffect, useRef } from 'react';
import { Send, User, MessageCircle, Mic, Image as ImageIcon, X, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = '/api';

const MimiChat = () => {
    const [messages, setMessages] = useState([
        { role: 'bot', content: 'Chào Mimi! Chị đã sẵn sàng hỗ trợ em học tập rồi đây. Hôm nay em muốn cùng chị khám phá chủ đề nào nào? ✨' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [selectedImage, setSelectedImage] = useState(null);
    const [isRecording, setIsRecording] = useState(false);
    const scrollRef = useRef(null);
    const fileInputRef = useRef(null);
    const recognitionRef = useRef(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    useEffect(() => {
        // Initialize Speech Recognition
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

    const handleSend = async () => {
        if ((!input.trim() && !selectedImage) || loading) return;

        const userMsg = input.trim();
        const hasImage = !!selectedImage;
        const currentImage = selectedImage; // closure capture

        setInput('');
        setSelectedImage(null);
        if (fileInputRef.current) fileInputRef.current.value = '';

        setMessages(prev => [...prev, {
            role: 'user',
            content: userMsg || '(Đã gửi một ảnh)',
            image: currentImage ? URL.createObjectURL(currentImage) : null
        }]);
        setLoading(true);

        try {
            let data;
            if (hasImage) {
                const formData = new FormData();
                formData.append('message', userMsg);
                formData.append('user_id', 'mimi_user');
                formData.append('file', currentImage);

                const res = await fetch(`${API_BASE}/mimi/chat/multimodal`, {
                    method: 'POST',
                    body: formData // No Content-Type, browser sets multipart/form-data
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
            setMessages(prev => [...prev, { role: 'bot', content: data.response }]);
        } catch (err) {
            console.error(err);
            setMessages(prev => [...prev, { role: 'bot', content: 'Ối, có lỗi gì đó rồi. Em thử lại xem sao nhé!' }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="chat-container">
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
                                    <img src={msg.image} alt="User Upload" style={{ maxWidth: '100%', borderRadius: '0.5rem', marginBottom: '0.5rem' }} />
                                )}
                                {msg.content}
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>
                {loading && <div className="loading" style={{ color: 'var(--primary)', textAlign: 'center', margin: '1rem 0' }}>Chị đang suy nghĩ... ✨</div>}
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
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleImageSelect}
                        accept="image/*"
                        style={{ display: 'none' }}
                    />

                    <button
                        className="action-btn"
                        onClick={() => fileInputRef.current?.click()}
                        title="Tải ảnh lên"
                    >
                        <ImageIcon size={20} />
                    </button>

                    <button
                        className={`action-btn ${isRecording ? 'recording' : ''}`}
                        onClick={toggleRecording}
                        title={isRecording ? "Đang nghe..." : "Nhấn để nói"}
                    >
                        <Mic size={20} />
                    </button>

                    <input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                        placeholder={isRecording ? "Chị đang nghe em nói nè..." : "Hãy hỏi chị bất cứ điều gì nha..."}
                    />

                    <button
                        className="send-btn"
                        onClick={handleSend}
                        disabled={loading || (!input.trim() && !selectedImage)}
                    >
                        <Send size={18} /> Gửi chị
                    </button>
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
