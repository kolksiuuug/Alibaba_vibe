import { Navigate, Route, Routes } from "react-router-dom";

import { RequireAuth } from "./components/common";
import { Layout } from "./components/Layout";
import { CardPage } from "./pages/analyst/CardPage";
import { QueuePage } from "./pages/analyst/QueuePage";
import { ApplicationPage } from "./pages/client/ApplicationPage";
import { HomePage } from "./pages/client/HomePage";
import { NewApplicationPage } from "./pages/client/NewApplicationPage";
import { LoginPage } from "./pages/LoginPage";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth role="client">
              <HomePage />
            </RequireAuth>
          }
        />
        <Route
          path="/new"
          element={
            <RequireAuth role="client">
              <NewApplicationPage />
            </RequireAuth>
          }
        />
        <Route
          path="/applications/:id"
          element={
            <RequireAuth role="client">
              <ApplicationPage />
            </RequireAuth>
          }
        />
        <Route
          path="/analyst"
          element={
            <RequireAuth role="analyst">
              <QueuePage />
            </RequireAuth>
          }
        />
        <Route
          path="/analyst/applications/:id"
          element={
            <RequireAuth role="analyst">
              <CardPage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
