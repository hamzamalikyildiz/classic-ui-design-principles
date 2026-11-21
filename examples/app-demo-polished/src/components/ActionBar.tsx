import { Button } from "@/components/ui/button";

export interface ActionBarProps {
  isEditing: boolean;
  onEdit: () => void;
  onSave: () => void;
}

// FALSE-POSITIVE TRAP #3: mutually exclusive solid primary CTAs in ternary
export function ActionBar({ isEditing, onEdit, onSave }: ActionBarProps) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-xl bg-card p-4 shadow-sm dark:border dark:border-white/10">
      <p className="text-sm text-muted-foreground">
        Değerlendirme notları yalnızca ekip içinde paylaşılır.
      </p>
      {isEditing ? (
        <Button type="button" size="lg" onClick={onSave}>
          Kaydet
        </Button>
      ) : (
        <Button type="button" size="lg" onClick={onEdit}>
          Düzenle
        </Button>
      )}
    </div>
  );
}
