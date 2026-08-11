import { AlertTriangle, PhoneCall } from "lucide-react";

export function EmergencyBanner() {
  return (
    <div className="sticky top-0 z-20 flex items-center gap-3 bg-red-600 px-4 py-3 text-white shadow-lg animate-fade-in">
      <AlertTriangle className="h-5 w-5 shrink-0" />
      <p className="flex-1 text-sm font-semibold">
        Your symptoms may require urgent medical evaluation. This is not a substitute for emergency care.
      </p>
      <span className="hidden items-center gap-1 text-xs font-medium sm:flex">
        <PhoneCall className="h-3.5 w-3.5" /> Call your local emergency number now
      </span>
    </div>
  );
}
