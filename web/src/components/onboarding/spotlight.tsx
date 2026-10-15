import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';

/**
 * Shared helpers for the guided tour and the auto-demo.
 * Goal: explain a feature WITHOUT hiding it. The real UI element is outlined with a pulsing ring
 * (no dimming, no click-blocking) and the explanation card is parked in whichever corner of the
 * stage overlaps the highlighted element and the open inspector the least.
 */

export interface Box {
  left: number;
  top: number;
  width: number;
  height: number;
}

/** First selector in the list that matches a visible element wins. */
const findTarget = (selectors: string[] | undefined): Element | null => {
  if (!selectors) return null;
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el) {
      const r = el.getBoundingClientRect();
      if (r.width > 0 && r.height > 0) return el;
    }
  }
  return null;
};

const sameBox = (a: Box | null, b: Box | null) =>
  a === b ||
  (!!a &&
    !!b &&
    Math.abs(a.left - b.left) < 1 &&
    Math.abs(a.top - b.top) < 1 &&
    Math.abs(a.width - b.width) < 1 &&
    Math.abs(a.height - b.height) < 1);

/**
 * Tracks the on-screen box of the first matching element. Re-queries every frame so it follows
 * moving buses, screen changes (target mounts late) and window resizes. Scrolls the target into
 * view once per `scrollKey` change.
 */
export function useTargetBox(selectors: string[] | undefined, scrollKey: unknown, active: boolean): Box | null {
  const [box, setBox] = useState<Box | null>(null);
  const lastScrollKey = useRef<unknown>(undefined);

  useEffect(() => {
    if (!active) {
      setBox(null);
      return;
    }
    let raf = 0;
    const tick = () => {
      const el = findTarget(selectors);
      if (el) {
        if (lastScrollKey.current !== scrollKey) {
          lastScrollKey.current = scrollKey;
          el.scrollIntoView?.({ block: 'nearest', inline: 'nearest' });
        }
        const r = el.getBoundingClientRect();
        const next: Box = { left: r.left, top: r.top, width: r.width, height: r.height };
        setBox(prev => (sameBox(prev, next) ? prev : next));
      } else {
        setBox(prev => (prev === null ? prev : null));
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, scrollKey, selectors?.join('|')]);

  return box;
}

const overlap = (a: Box, b: Box) => {
  const w = Math.min(a.left + a.width, b.left + b.width) - Math.max(a.left, b.left);
  const h = Math.min(a.top + a.height, b.top + b.height) - Math.max(a.top, b.top);
  return w > 0 && h > 0 ? w * h : 0;
};

const pad = (b: Box, p: number): Box => ({
  left: b.left - p,
  top: b.top - p,
  width: b.width + p * 2,
  height: b.height + p * 2
});

/**
 * Picks the stage corner for a floating card of `cardWidth` that covers the target (and the open
 * inspector drawer) the least. `cardRef` is measured so tall cards are accounted for.
 */
export function useCornerPlacement(
  target: Box | null,
  cardWidth: number,
  cardRef: React.RefObject<HTMLElement | null>,
  active: boolean
): React.CSSProperties {
  const [style, setStyle] = useState<React.CSSProperties>({ right: 16, bottom: 92 });

  useLayoutEffect(() => {
    if (!active) return;
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    // Phone width: dock full-width above the time bar
    if (vw < 720) {
      setStyle({ left: 12, right: 12, bottom: 92, width: 'auto' });
      return;
    }

    const h = cardRef.current?.offsetHeight ?? 260;
    const w = Math.min(cardWidth, vw - 32);
    const margin = 16;
    const stageLeft = (document.querySelector('.icon-rail')?.getBoundingClientRect().right ?? 0) + margin;
    const stageTop = (document.querySelector('.status-ribbon')?.getBoundingClientRect().bottom ?? 56) + margin;
    const stageBottom =
      (document.querySelector('.time-deck')?.getBoundingClientRect().top ?? vh - 76) - margin;
    const stageRight = vw - margin;

    const corners: Box[] = [
      { left: stageRight - w, top: stageBottom - h, width: w, height: h }, // bottom-right
      { left: stageLeft, top: stageBottom - h, width: w, height: h }, // bottom-left
      { left: stageRight - w, top: stageTop, width: w, height: h }, // top-right
      { left: stageLeft, top: stageTop, width: w, height: h } // top-left
    ];

    // [box, weight]: the highlighted element matters most, then an open inspector, then map controls
    const obstacles: [Box, number][] = [];
    if (target) obstacles.push([pad(target, 14), 4]);
    const toBox = (el: Element): Box => {
      const r = el.getBoundingClientRect();
      return { left: r.left, top: r.top, width: r.width, height: r.height };
    };
    const drawer = document.querySelector('.inspector-drawer.open');
    if (drawer) obstacles.push([toBox(drawer), 2]);
    document.querySelectorAll('.map-toolbar, .map-legend-panel').forEach(el => obstacles.push([toBox(el), 1]));

    let best = corners[0];
    let bestScore = Infinity;
    corners.forEach(c => {
      const score = obstacles.reduce((sum, [o, weight]) => sum + overlap(c, o) * weight, 0);
      if (score < bestScore) {
        best = c;
        bestScore = score;
      }
    });

    setStyle({ left: best.left, top: best.top, width: w });
  }, [active, target?.left, target?.top, target?.width, target?.height, cardWidth, cardRef]);

  return style;
}

/** Pulsing outline drawn over the real UI element being explained. Never blocks clicks. */
export const SpotlightRing: React.FC<{ box: Box | null }> = ({ box }) => {
  if (!box) return null;
  const p = 6;
  return (
    <div
      aria-hidden="true"
      className="spotlight-ring"
      style={{
        position: 'fixed',
        left: box.left - p,
        top: box.top - p,
        width: box.width + p * 2,
        height: box.height + p * 2,
        zIndex: 290
      }}
    />
  );
};
