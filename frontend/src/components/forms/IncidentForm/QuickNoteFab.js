import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import PropTypes from 'prop-types';
import { Button, Form, Icon } from 'semantic-ui-react';

const PLACEHOLDER =
  'Short notes for context (saved with the incident; used when generating narrative)';

const QuickNoteFab = ({ value, onChange, disabled, containerRef }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [scrollTarget, setScrollTarget] = useState(null);
  const rootRef = useRef(null);

  // Detect whether we are inside a Semantic UI Modal.Content scroll area.
  // If so, portal into that element and use sticky positioning so the FAB
  // stays inside the scrollable content and never touches Modal.Actions.
  useLayoutEffect(() => {
    const el = containerRef?.current;
    if (!el) {
      setScrollTarget(null);
      return;
    }
    const found = el.closest('.scrolling.content') ?? null;
    setScrollTarget(found);
  }, [containerRef]);

  const hasContent = Boolean((value || '').trim());

  useEffect(() => {
    if (!isOpen) return undefined;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setIsOpen(false);
    };

    const handleMouseDown = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handleMouseDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handleMouseDown);
    };
  }, [isOpen]);

  const toggleOpen = () => {
    if (disabled) return;
    setIsOpen((open) => !open);
  };

  const inScroll = Boolean(scrollTarget);

  const fab = (
    <div
      className={`quick-note-fab${inScroll ? ' quick-note-fab--in-scroll' : ' quick-note-fab--fixed'}`}
      ref={rootRef}
    >
      {isOpen && (
        <div className="quick-note-fab__panel" role="dialog" aria-label="Quick note">
          <div className="quick-note-fab__panel-header">
            <span className="quick-note-fab__panel-title">Quick note</span>
            <Button
              type="button"
              icon="close"
              basic
              size="mini"
              aria-label="Close quick note"
              onClick={() => setIsOpen(false)}
            />
          </div>
          <Form className="quick-note-fab__form">
            <Form.TextArea
              placeholder={PLACEHOLDER}
              value={value || ''}
              onChange={(e, { value: next }) => onChange(next)}
              disabled={disabled}
            />
          </Form>
        </div>
      )}
      <button
        type="button"
        className={`quick-note-fab__button${isOpen ? ' quick-note-fab__button--open' : ''}`}
        onClick={toggleOpen}
        disabled={disabled}
        aria-label={isOpen ? 'Close quick note' : 'Open quick note'}
        aria-expanded={isOpen}
      >
        <Icon name="sticky note outline" size="large" />
        {hasContent && <span className="quick-note-fab__badge" aria-hidden="true" />}
      </button>
    </div>
  );

  return createPortal(fab, scrollTarget || document.body);
};

QuickNoteFab.propTypes = {
  value: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  containerRef: PropTypes.shape({ current: PropTypes.instanceOf(Element) }),
};

QuickNoteFab.defaultProps = {
  value: '',
  disabled: false,
  containerRef: null,
};

export default QuickNoteFab;
