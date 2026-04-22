import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { getSiteBanner } from "@/api/siteBanner";
import "./SiteBanner.css";

const DISMISSED_KEY = "siteBannerDismissedVersion";

export default function SiteBanner() {
  const { data } = useQuery({
    queryKey: ["siteBanner"],
    queryFn: getSiteBanner,
    staleTime: 60_000,
    retry: 1,
  });

  const version = data?.updated_at ?? "0";
  const [dismissedVersion, setDismissedVersion] = useState(() => {
    try {
      return localStorage.getItem(DISMISSED_KEY) ?? "";
    } catch {
      return "";
    }
  });

  const isVisible = useMemo(() => {
    if (!data?.is_enabled) return false;
    if (!data.message?.trim()) return false;
    return dismissedVersion !== version;
  }, [data?.is_enabled, data?.message, dismissedVersion, version]);

  if (!isVisible) return null;

  const onClose = () => {
    try {
      localStorage.setItem(DISMISSED_KEY, version);
    } catch {
      // ignore
    }
    setDismissedVersion(version);
  };

  return (
    <div className="site-banner" role="status" aria-live="polite">
      <div className="site-banner__card">
        <button
          type="button"
          onClick={onClose}
          aria-label="Закрыть уведомление"
          className="site-banner__close"
        >
          ✕
        </button>
        <div className="site-banner__text">{data?.message}</div>
      </div>
    </div>
  );
}
