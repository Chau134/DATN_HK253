import { useEffect, useRef, useState } from 'react';
import classNames from 'classnames/bind';
import { useLocation, useNavigate } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faComments, faCompress, faExpand, faImage, faPaperPlane, faSpinner, faThumbsDown, faThumbsUp, faXmark } from '@fortawesome/free-solid-svg-icons';
import { aiApi, formatAiWarnings, getApiError } from '../../api/aiApi';
import { getAssistantSessionId, getAssistantUserId } from '../../utils/assistantSession';
import { cropBoxOf, imagePayloadFromFile, imageWithDetections } from '../../utils/aiImage';
import { formatCurrencyFromDb } from '../../utils/price';
import ProductCard from '../../components/ProductCard';
import styles from './ChatBot.module.scss';

const cx = classNames.bind(styles);
const HIDDEN_PATH_PREFIXES = ['/admin', '/login', '/register'];

function buildFilterChips(filters) {
    if (!filters) return [];
    const chips = [];
    if (filters.category) chips.push(filters.category);
    if (filters.brand) chips.push(filters.brand);
    (filters.colors || []).forEach((color) => chips.push(color));
    (filters.sizes || []).forEach((size) => chips.push(`Size ${size}`));
    if (filters.gender) chips.push(filters.gender);
    if (filters.material) chips.push(filters.material);
    if (filters.min_price != null && filters.max_price != null) {
        chips.push(`${formatCurrencyFromDb(filters.min_price)} – ${formatCurrencyFromDb(filters.max_price)}`);
    } else if (filters.min_price != null) {
        chips.push(`Từ ${formatCurrencyFromDb(filters.min_price)}`);
    } else if (filters.max_price != null) {
        chips.push(`Đến ${formatCurrencyFromDb(filters.max_price)}`);
    }
    return chips;
}

function ChatBot() {
    const location = useLocation();
    const navigate = useNavigate();
    const sessionId = useRef(getAssistantSessionId());
    const userId = useRef(getAssistantUserId());
    const messagesEndRef = useRef(null);
    const [isOpen, setIsOpen] = useState(false);
    const [isExpanded, setIsExpanded] = useState(false);
    const [isSending, setIsSending] = useState(false);
    const [message, setMessage] = useState('');
    const [image, setImage] = useState(null);
    const [messages, setMessages] = useState([
        {
            role: 'assistant',
            content: 'Chào bạn 👋 Em có thể cùng bạn tìm đồ, so sánh vài lựa chọn hoặc gợi ý theo phong cách và ngân sách.',
        },
    ]);

    const shouldHide = HIDDEN_PATH_PREFIXES.some((prefix) => location.pathname.startsWith(prefix));

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isOpen, isSending]);

    const handleImagePick = async (event) => {
        const file = event.target.files?.[0];
        event.target.value = '';
        if (!file) return;
        try {
            const picked = await imagePayloadFromFile(file);
            setImage(picked);
            const detected = await imageWithDetections(picked);
            setImage((current) => (current && current.filename === picked.filename ? detected : current));
        } catch (error) {
            setImage(null);
            setMessages((prevMessages) => [...prevMessages, { role: 'assistant', content: getApiError(error), error: true }]);
        }
    };

    const sendMessage = async (event) => {
        event.preventDefault();
        const text = message.trim();
        if ((!text && !image) || isSending) return;

        const outgoingImage = image;
        const userContent = text || (outgoingImage ? 'Tìm sản phẩm giống ảnh này' : '');
        setMessage('');
        setImage(null);
        setIsSending(true);
        setMessages((prevMessages) => [...prevMessages, { role: 'user', content: userContent, imagePreview: outgoingImage?.preview }]);

        try {
            const data = await aiApi.assistant({
                session_id: sessionId.current,
                user_id: userId.current,
                message: userContent,
                image: outgoingImage?.payload,
                crop_box: cropBoxOf(outgoingImage),
                locale: 'vi-VN',
            });

            setMessages((prevMessages) => [
                ...prevMessages,
                {
                    role: 'assistant',
                    content: data?.message || 'Mình đã nhận được yêu cầu, nhưng chưa có câu trả lời phù hợp.',
                    chatMessageId: data?.chat_message_id,
                    products: data?.products || [],
                    filters: data?.filters || null,
                    rewrittenQuery: data?.rewritten_query || '',
                    warnings: data?.warnings || [],
                },
            ]);
        } catch (error) {
            setMessages((prevMessages) => [
                ...prevMessages,
                {
                    role: 'assistant',
                    content: getApiError(error),
                    error: true,
                },
            ]);
        } finally {
            setIsSending(false);
        }
    };

    const sendFeedback = async (chatMessageId, helpful) => {
        if (!chatMessageId) return;
        setMessages((prevMessages) => prevMessages.map((item) => (
            item.chatMessageId === chatMessageId ? { ...item, feedback: helpful } : item
        )));
        try {
            await aiApi.assistantFeedback({
                chat_message_id: chatMessageId,
                user_id: userId.current,
                helpful,
                rating: helpful ? 5 : 1,
                feedback_type: helpful ? 'helpful' : 'not_helpful',
            });
        } catch {
            setMessages((prevMessages) => prevMessages.map((item) => (
                item.chatMessageId === chatMessageId ? { ...item, feedback: undefined } : item
            )));
        }
    };

    if (shouldHide) {
        return null;
    }

    return (
        <>
            {isOpen ? (
                <div className={cx('wrapper', { expanded: isExpanded })}>
                    <header className={cx('header')}>
                        <div className={cx('header-info')}>
                            <div className={cx('avatar')}>
                                <FontAwesomeIcon icon={faComments} />
                            </div>
                            <div>
                                <h2>Trợ lý mua sắm</h2>
                                <span className={cx('status')}>Đang sẵn sàng</span>
                            </div>
                        </div>
                        <div className={cx('header-actions')}>
                            <button
                                type="button"
                                onClick={() => setIsExpanded((current) => !current)}
                                className={cx('icon-btn')}
                                aria-label={isExpanded ? 'Thu nhỏ' : 'Phóng to'}
                            >
                                <FontAwesomeIcon icon={isExpanded ? faCompress : faExpand} />
                            </button>
                            <button type="button" onClick={() => setIsOpen(false)} className={cx('icon-btn')} aria-label="Đóng chat">
                                <FontAwesomeIcon icon={faXmark} />
                            </button>
                        </div>
                    </header>

                    <main className={cx('main')}>
                        {messages.map((item, index) => {
                            const chips = item.role === 'assistant' ? buildFilterChips(item.filters) : [];
                            const products = item.products || [];
                            const warningText = formatAiWarnings(item.warnings);
                            return (
                                <div className={cx('message-row')} key={`${item.role}-${index}`}>
                                    <div className={cx(item.role === 'user' ? 'user-message' : 'bot-message', { error: item.error })}>
                                        {item.imagePreview && (
                                            <img className={cx('message-image')} src={item.imagePreview} alt="Ảnh đã gửi" />
                                        )}
                                        {item.content}
                                    </div>

                                    {item.role === 'assistant' && item.rewrittenQuery && (
                                        <div className={cx('rewritten-query')}>Đang tìm cho: «{item.rewrittenQuery}»</div>
                                    )}

                                    {chips.length > 0 && (
                                        <div className={cx('filter-chips')}>
                                            {chips.map((chip, chipIndex) => (
                                                <span className={cx('chip')} key={`${chip}-${chipIndex}`}>{chip}</span>
                                            ))}
                                        </div>
                                    )}

                                    {products.length > 0 && (
                                        <div className={cx('product-list')}>
                                            {products.map((product) => (
                                                <ProductCard key={product.product_id || product.id} product={product} variant="compact" />
                                            ))}
                                        </div>
                                    )}

                                    {warningText && (
                                        <div className={cx('warning-badge')}>
                                            {warningText}
                                        </div>
                                    )}

                                    {item.role === 'assistant' && item.chatMessageId && !item.error && (
                                        <div className={cx('feedback-actions')}>
                                            <span>Phản hồi này hữu ích?</span>
                                            <button
                                                type="button"
                                                className={cx({ active: item.feedback === true })}
                                                onClick={() => sendFeedback(item.chatMessageId, true)}
                                                aria-label="Phản hồi hữu ích"
                                            >
                                                <FontAwesomeIcon icon={faThumbsUp} />
                                            </button>
                                            <button
                                                type="button"
                                                className={cx({ active: item.feedback === false })}
                                                onClick={() => sendFeedback(item.chatMessageId, false)}
                                                aria-label="Phản hồi chưa hữu ích"
                                            >
                                                <FontAwesomeIcon icon={faThumbsDown} />
                                            </button>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                        {isSending && (
                            <div className={cx('message-row')}>
                                <div className={cx('bot-message', 'typing')}>
                                    <FontAwesomeIcon icon={faSpinner} spin />
                                    <span>Đang trả lời...</span>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </main>

                    <footer className={cx('footer')}>
                        {image && (
                            <div className={cx('image-attachment')}>
                                <img src={image.preview} alt={image.filename} />
                                <button type="button" onClick={() => setImage(null)} aria-label="Xóa ảnh">
                                    <FontAwesomeIcon icon={faXmark} />
                                </button>
                            </div>
                        )}
                        <form onSubmit={sendMessage} className={cx('input-form')}>
                            <label className={cx('attach-btn')} aria-label="Đính ảnh">
                                <FontAwesomeIcon icon={faImage} />
                                <input type="file" accept="image/*" onChange={handleImagePick} disabled={isSending} />
                            </label>
                            <input
                                type="text"
                                value={message}
                                onChange={(event) => setMessage(event.target.value)}
                                placeholder="Hỏi về sản phẩm, size, outfit..."
                                disabled={isSending}
                            />
                            <button type="submit" disabled={(!message.trim() && !image) || isSending} aria-label="Gửi tin nhắn">
                                <FontAwesomeIcon icon={isSending ? faSpinner : faPaperPlane} spin={isSending} />
                            </button>
                        </form>
                        <button type="button" className={cx('full-page-link')} onClick={() => navigate('/tu-van')}>
                            Mở trang tư vấn đầy đủ
                        </button>
                    </footer>
                </div>
            ) : (
                <div className={cx('show-chatbox')}>
                    <button type="button" onClick={() => setIsOpen(true)} aria-label="Mở trợ lý mua sắm">
                        <FontAwesomeIcon icon={faComments} />
                    </button>
                </div>
            )}
        </>
    );
}

export default ChatBot;
