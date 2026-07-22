/**
 * Sidebar Drawer Gesture — horizontal swipe to open/close.
 *
 *  - Swipe right from left edge (< 50px): open sidebar drawer
 *  - Swipe left on open sidebar: close sidebar drawer
 *
 * Works on iOS Safari, Android Chrome, and all touch-capable browsers.
 * Single-finger horizontal swipe only — does not interfere with
 * vertical scroll or two-finger gestures.
 */

const SWIPE_THRESHOLD = 50; // px — minimum horizontal distance to trigger
const EDGE_WIDTH = 50; // px — left edge zone for swipe-to-open

let edgeSwipeStartX = -1;
let sidebarSwipeStartX = -1;
let listenersActive = false;

function getSidebar(): HTMLElement | null {
  return document.getElementById("workspace-sidebar");
}

function isDrawerOpen(): boolean {
  return getSidebar()?.classList.contains("drawer-open") ?? false;
}

function openDrawer(): void {
  const sidebar = getSidebar();
  if (!sidebar || isDrawerOpen()) return;
  sidebar.classList.add("drawer-open");
  document.body.style.overflow = "hidden";
}

function closeDrawer(): void {
  const sidebar = getSidebar();
  if (!sidebar || !isDrawerOpen()) return;
  sidebar.classList.remove("drawer-open");
  document.body.style.overflow = "";
}

// --- Swipe right from left edge → open drawer ---

function onEdgeTouchStart(e: TouchEvent): void {
  const x = e.touches[0].clientX;
  edgeSwipeStartX = x < EDGE_WIDTH ? x : -1;
  if (edgeSwipeStartX >= 0) {
    console.log(`[DrawerGesture] Edge touch start at x=${x}`);
  }
}

function onEdgeTouchEnd(e: TouchEvent): void {
  if (edgeSwipeStartX < 0) return;
  const dx = e.changedTouches[0].clientX - edgeSwipeStartX;
  console.log(
    `[DrawerGesture] Edge swipe dx=${dx} (threshold=${SWIPE_THRESHOLD})`,
  );
  if (dx > SWIPE_THRESHOLD) {
    console.log("[DrawerGesture] Opening drawer");
    openDrawer();
  }
  edgeSwipeStartX = -1;
}

// --- Swipe left on open sidebar → close drawer ---

function onSidebarTouchStart(e: TouchEvent): void {
  sidebarSwipeStartX = e.touches[0].clientX;
}

function onSidebarTouchEnd(e: TouchEvent): void {
  if (sidebarSwipeStartX < 0) return;
  const dx = e.changedTouches[0].clientX - sidebarSwipeStartX;
  if (dx < -SWIPE_THRESHOLD) closeDrawer();
  sidebarSwipeStartX = -1;
}

// --- Init ---

export function init(): void {
  if (listenersActive) return;

  document.addEventListener("touchstart", onEdgeTouchStart, { passive: true });
  document.addEventListener("touchend", onEdgeTouchEnd, { passive: true });

  const sidebarInner = document.getElementById("sidebar-inner");
  sidebarInner?.addEventListener("touchstart", onSidebarTouchStart, {
    passive: true,
  });
  sidebarInner?.addEventListener("touchend", onSidebarTouchEnd, {
    passive: true,
  });

  listenersActive = true;
  console.log("[DrawerGesture] Initialized");
}

// Auto-init on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
