import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

type RetryableRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean;
};

const getToken = async (key: string) => {
  if (Platform.OS === "web") {
    return localStorage.getItem(key);
  }
  return await SecureStore.getItemAsync(key);
};

const setToken = async (key: string, value: string) => {
  if (Platform.OS === "web") {
    localStorage.setItem(key, value);
  } else {
    await SecureStore.setItemAsync(key, value);
  }
};

const deleteToken = async (key: string) => {
  if (Platform.OS === "web") {
    localStorage.removeItem(key);
  } else {
    await SecureStore.deleteItemAsync(key);
  }
};

let onUnauthorized: (() => void) | null = null;

export const setUnauthorizedHandler = (handler: (() => void) | null) => {
  onUnauthorized = handler;
};

export const clearStoredSession = async () => {
  await deleteToken("access_token");
  await deleteToken("refresh_token");
};

const ip = "172.20.10.10";  //modify with your IP address


const apiClient = axios.create({
  baseURL: `http://${ip}:8000`,
  headers: {
    "Content-Type": "application/json",
  },
});

let isRefreshing = false;
let refreshPromise: Promise<string> | null = null;

const refreshAccessToken = async (): Promise<string> => {
  const refreshToken = await getToken("refresh_token");

  if (!refreshToken) {
    throw new Error("No hi ha refresh token");
  }

  const response = await axios.post(
    `${apiClient.defaults.baseURL}/auth/refresh`,
    {
      refresh_token: refreshToken,
    },
  );

  const { access_token, refresh_token: newRefreshToken } = response.data ?? {};

  if (!access_token) {
    throw new Error("No s'ha rebut un access token nou");
  }

  await setToken("access_token", access_token);

  // Importantíssim: només sobreescriure si el backend realment envia un refresh nou
  if (newRefreshToken) {
    await setToken("refresh_token", newRefreshToken);
  }

  return access_token;
};

apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const token = await getToken("access_token");

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error),
);

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableRequestConfig | undefined;
    const status = error.response?.status;

    if (!originalRequest) {
      return Promise.reject(error);
    }

    const isRefreshCall = originalRequest.url?.includes("/auth/refresh");

    if (status === 401 && !originalRequest._retry && !isRefreshCall) {
      originalRequest._retry = true;

      try {
        if (!isRefreshing) {
          isRefreshing = true;
          refreshPromise = refreshAccessToken();
        }

        const newAccessToken = await refreshPromise!;
        originalRequest.headers = originalRequest.headers ?? {};
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;

        return apiClient(originalRequest);
      } catch (refreshError) {
        await clearStoredSession();

        if (onUnauthorized) {
          onUnauthorized();
        }

        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
        refreshPromise = null;
      }
    }

    if (status === 401) {
      await clearStoredSession();

      if (onUnauthorized) {
        onUnauthorized();
      }
    }

    if (
      (error as any)?.code === "ECONNABORTED" ||
      error.message?.toLowerCase().includes("timeout")
    ) {
      return Promise.reject(
        "El servidor tarda massa a respondre. Torna-ho a provar.",
      );
    }

    return Promise.reject(error);
  },
);

export default apiClient;
