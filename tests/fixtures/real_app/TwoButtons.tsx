import React from 'react';

declare function Button(props: { className?: string; children: React.ReactNode }): React.ReactElement;

export function TwoButtons() {
  return (
    <div className="flex items-center gap-4">
      <Button className="bg-slate-900 text-white">Kaydet</Button>
      <Button className="bg-blue-600 text-white">Yayınla</Button>
    </div>
  );
}
