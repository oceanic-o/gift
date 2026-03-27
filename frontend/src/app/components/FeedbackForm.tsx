import { motion } from 'motion/react';
import { useState } from 'react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { MessageSquare, Send, X } from 'lucide-react';

interface FeedbackFormProps {
  isOpen: boolean;
  onClose: () => void;
}

export function FeedbackForm({ isOpen, onClose }: FeedbackFormProps) {
  const [feedback, setFeedback] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Mock submission
    setSubmitted(true);
    setTimeout(() => {
      setFeedback('');
      setSubmitted(false);
      onClose();
    }, 2000);
  };

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, y: 50 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.9, y: 50 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-gradient-to-br from-white via-emerald-50 to-teal-50 rounded-3xl p-8 max-w-lg w-full shadow-2xl border-4 border-emerald-100 relative"
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-full hover:bg-emerald-100 transition-colors"
        >
          <X size={20} />
        </button>

        {!submitted ? (
          <>
            <div className="flex items-center gap-3 mb-6">
              <MessageSquare className="text-emerald-600" size={32} />
              <h3 className="text-3xl font-bold bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent">
                Share Your Feedback
              </h3>
            </div>

            <p className="text-gray-600 mb-6">
              We'd love to hear your thoughts! Your feedback helps us improve Giftora.
            </p>

            <form onSubmit={handleSubmit}>
              <Textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Tell us what you think..."
                required
                className="min-h-[150px] mb-6 border-2 border-emerald-200 focus:border-emerald-500"
              />

              <Button
                type="submit"
                className="w-full bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 py-6"
              >
                <Send className="mr-2" size={20} />
                Submit Feedback
              </Button>
            </form>
          </>
        ) : (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="text-center py-12"
          >
            <motion.div
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 0.5, repeat: Infinity }}
              className="text-6xl mb-4"
            >
              ✅
            </motion.div>
            <h3 className="text-2xl font-bold text-emerald-600 mb-2">Thank You!</h3>
            <p className="text-gray-600">Your feedback has been submitted.</p>
          </motion.div>
        )}
      </motion.div>
    </motion.div>
  );
}
