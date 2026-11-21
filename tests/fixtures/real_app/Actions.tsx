import React from 'react';

declare function Button(props: { className?: string; children: React.ReactNode }): React.ReactElement;

export function Actions({ isEditing }: { isEditing: boolean }) {
  return (
    <div className="flex items-center gap-2">
      {isEditing ? (
        <Button className="bg-slate-900 text-white">Kaydet</Button>
      ) : (
        <Button className="bg-blue-600 text-white">Düzenle</Button>
      )}
    </div>
  );
}
