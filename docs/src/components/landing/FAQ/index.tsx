import React, {useState, type ReactNode} from 'react';
import styles from './styles.module.css';

export interface FAQItem {
  question: string;
  answer: ReactNode;
}

interface FAQProps {
  items: FAQItem[];
  /** Allow multiple panels open at once. Default false (single-open). */
  multiple?: boolean;
}

/**
 * Accessible FAQ accordion. Single-open by default; pass `multiple` to let
 * several answers stay expanded. Each row is a glass surface that lifts to
 * frost when open.
 */
export default function FAQ({items, multiple = false}: FAQProps): ReactNode {
  const [open, setOpen] = useState<number[]>([]);

  const toggle = (index: number) => {
    setOpen((current) => {
      if (current.includes(index)) {
        return current.filter((i) => i !== index);
      }
      return multiple ? [...current, index] : [index];
    });
  };

  return (
    <div className={styles.list}>
      {items.map((item, index) => {
        const isOpen = open.includes(index);
        return (
          <div
            key={item.question}
            className={`${styles.item} ${isOpen ? styles.itemOpen : ''}`}>
            <button
              type="button"
              className={styles.trigger}
              aria-expanded={isOpen}
              onClick={() => toggle(index)}>
              <span className={styles.question}>{item.question}</span>
              <span className={styles.icon} aria-hidden="true">
                {isOpen ? '−' : '+'}
              </span>
            </button>
            {isOpen && <div className={styles.answer}>{item.answer}</div>}
          </div>
        );
      })}
    </div>
  );
}
