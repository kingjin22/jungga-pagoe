"use client";
import { useEffect } from "react";
import { trackPageView } from "@/lib/tracking";

export default function PageViewTracker() {
  useEffect(() => {
    trackPageView();
  }, []);
  return null;
}
