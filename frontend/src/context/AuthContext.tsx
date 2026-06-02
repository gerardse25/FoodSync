import { router } from "expo-router";
import React, { createContext, useContext, useEffect, useState } from "react";
import { authService } from "../services/authService";
import { clearStoredSession, setUnauthorizedHandler } from "../services/client";
import { homeService } from "../services/homeService";

type AuthContextType = {
  session: any | null;
  isLoading: boolean;
  hasHome: boolean;
  setHasHome: (hasHome: boolean) => void;
  checkSession: () => Promise<void>;
  setSession: (session: any | null) => void;
  logoutAndRedirect: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [session, setSession] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasHome, setHasHome] = useState(false);

  const logoutAndRedirect = async () => {
    await clearStoredSession();
    setSession(null);
    setHasHome(false);
    router.replace("/");
  };

  const checkSession = async () => {
    setIsLoading(true);

    try {
      const data = await authService.verify();
      setSession(data.user);

      try {
        const homeData = await homeService.syncHome();
        setHasHome(!!homeData.home_active);
      } catch {
        setHasHome(false);
      }
    } catch {
      setSession(null);
      setHasHome(false);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setSession(null);
      setHasHome(false);
      router.replace("/");
    });

    checkSession();

    return () => {
      setUnauthorizedHandler(null);
    };
  }, []);

  return (
    <AuthContext.Provider
      value={{
        session,
        isLoading,
        hasHome,
        setHasHome,
        checkSession,
        setSession,
        logoutAndRedirect,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
