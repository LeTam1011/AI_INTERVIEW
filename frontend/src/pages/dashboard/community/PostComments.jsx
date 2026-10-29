import React, { useCallback, useEffect, useState } from 'react';
import { Send, Trash2, LoaderCircle } from 'lucide-react';
import { api } from '../../../services/api';
import { useAuth } from '../../../context/AuthContext';

export default function PostComments({ postId, onCountChange }) {
  const { user } = useAuth();
  const [comments, setComments] = useState([]);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const loadComments = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getPostComments(postId);
      setComments(data.comments || []);
      setError('');
    } catch (err) {
      setError(err.message || 'Không thể tải bình luận.');
    } finally {
      setLoading(false);
    }
  }, [postId]);

  useEffect(() => {
    loadComments();
  }, [loadComments]);

  const submitComment = async (event) => {
    event.preventDefault();
    const value = content.trim();
    if (!value || submitting) return;

    setSubmitting(true);
    setError('');
    try {
      const data = await api.addPostComment(postId, value);
      if (data.comment) {
        setComments(current => [...current, data.comment]);
        onCountChange?.(1);
      }
      setContent('');
    } catch (err) {
      setError(err.message || 'Không thể thêm bình luận.');
    } finally {
      setSubmitting(false);
    }
  };

  const removeComment = async (commentId) => {
    try {
      await api.deletePostComment(commentId);
      setComments(current => current.filter(comment => comment.id !== commentId));
      onCountChange?.(-1);
    } catch (err) {
      setError(err.message || 'Không thể xóa bình luận.');
    }
  };

  return (
    <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid var(--border)' }}>
      {loading ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Đang tải bình luận...</div>
      ) : comments.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '12px' }}>
          Chưa có bình luận. Hãy là người đầu tiên trao đổi.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '14px' }}>
          {comments.map(comment => {
            const canDelete = user?.role === 'admin' || user?.id === comment.author_id;
            return (
              <div key={comment.id} style={{ display: 'flex', gap: '9px', alignItems: 'flex-start' }}>
                <img
                  src={comment.author_avatar || '/avatar-default.jpg'}
                  alt="avatar"
                  style={{ width: '28px', height: '28px', borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '12px', fontWeight: 700 }}>{comment.author_name}</span>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                      {new Date(comment.created_at).toLocaleString('vi-VN')}
                    </span>
                    {canDelete && (
                      <button
                        type="button"
                        onClick={() => removeComment(comment.id)}
                        title="Xóa bình luận"
                        style={{ marginLeft: 'auto', color: 'var(--text-muted)', background: 'none', border: 0, cursor: 'pointer', padding: 2 }}
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: 1.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {comment.content}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {error && <div style={{ color: 'oklch(68% 0.2 25)', fontSize: '12px', marginBottom: '8px' }}>{error}</div>}

      <form onSubmit={submitComment} style={{ display: 'flex', gap: '8px' }}>
        <input
          value={content}
          onChange={event => setContent(event.target.value)}
          placeholder="Viết bình luận..."
          maxLength={2000}
          className="input-field"
          style={{ flex: 1, minWidth: 0, padding: '9px 12px', fontSize: '13px' }}
        />
        <button
          type="submit"
          disabled={submitting || !content.trim()}
          className="btn-primary"
          title="Gửi bình luận"
          style={{ padding: '9px 12px', opacity: submitting || !content.trim() ? 0.55 : 1 }}
        >
          {submitting ? <LoaderCircle size={16} className="animate-spin" /> : <Send size={16} />}
        </button>
      </form>
    </div>
  );
}
