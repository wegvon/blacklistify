import { Toaster } from "react-hot-toast";
import AuthProvider from "./services/auth/authProvider";
import Routes from "./routes";

function App() {
  return (
    <AuthProvider>
      <Routes />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1e293b',
            color: '#e2e8f0',
            border: '1px solid #334155',
          },
        }}
      />
    </AuthProvider>
  );
}

export default App;
