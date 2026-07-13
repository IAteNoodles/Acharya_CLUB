import { LoaderCircle } from 'lucide-react';

export function FullPageSpinner({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="grid min-h-screen place-items-center bg-background" role="status">
      <div className="flex flex-col items-center gap-3">
        <LoaderCircle aria-hidden="true" className="h-6 w-6 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
    </div>
  );
}
