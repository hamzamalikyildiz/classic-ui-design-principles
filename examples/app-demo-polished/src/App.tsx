import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { CvDetailPage } from "@/pages/CvDetailPage";
import { CvListPage } from "@/pages/CvListPage";
import { LoginPage } from "@/pages/LoginPage";
import { SettingsPage } from "@/pages/SettingsPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/cv" element={<CvListPage />} />
        <Route path="/cv/:id" element={<CvDetailPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/cv" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
