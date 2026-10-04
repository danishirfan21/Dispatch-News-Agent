import { useEffect, useRef, useState } from 'react'

/** Cumulative downward scroll (px) before the header hides. */
const HIDE_THRESHOLD = 48
/** Always show the header within this many px of the top. */
const TOP_OFFSET = 80
/** Pointer distance (px) from the viewport top that reveals the header. */
const POINTER_TRIGGER_ZONE = 32

export function useAutoHideHeader() {
  const [scrollVisible, setScrollVisible] = useState(true)
  const [interacting, setInteracting] = useState(false)

  const lastY = useRef(0)
  const accumulatedDown = useRef(0)
  const frameRequested = useRef(false)

  useEffect(() => {
    lastY.current = window.scrollY

    function processScroll() {
      frameRequested.current = false
      const y = window.scrollY
      const diff = y - lastY.current

      if (y <= TOP_OFFSET) {
        setScrollVisible(true)
        accumulatedDown.current = 0
      } else if (diff > 0) {
        accumulatedDown.current += diff
        if (accumulatedDown.current > HIDE_THRESHOLD) {
          setScrollVisible(false)
        }
      } else if (diff < 0) {
        accumulatedDown.current = 0
        setScrollVisible(true)
      }

      lastY.current = y
    }

    function onScroll() {
      if (frameRequested.current) return
      frameRequested.current = true
      requestAnimationFrame(processScroll)
    }

    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    // Only desktop pointers with real hover get the near-top reveal zone;
    // touch/coarse pointers must rely on upward scrolling only.
    const supportsHoverReveal = window.matchMedia(
      '(hover: hover) and (pointer: fine)',
    ).matches
    if (!supportsHoverReveal) return

    function onPointerMove(event: PointerEvent) {
      if (event.clientY <= POINTER_TRIGGER_ZONE) {
        setScrollVisible(true)
      }
    }

    window.addEventListener('pointermove', onPointerMove, { passive: true })
    return () => window.removeEventListener('pointermove', onPointerMove)
  }, [])

  const visible = scrollVisible || interacting

  const headerInteractionProps = {
    onFocus: () => setInteracting(true),
    onBlur: (event: React.FocusEvent<HTMLElement>) => {
      if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
        setInteracting(false)
      }
    },
    onMouseEnter: () => setInteracting(true),
    onMouseLeave: () => setInteracting(false),
  }

  return { visible, headerInteractionProps }
}
