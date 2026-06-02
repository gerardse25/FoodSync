import apiClient from "./client";

export interface NotificationItem {
  id: string;
  tipus:
    | "EXPIRED"
    | "EXPIRING_SOON"
    | "HOME_MEMBER_JOINED"
    | "HOME_PRODUCT_ADDED"
    | string;
  id_producte?: string | null;
  nom_producte?: string | null;
  data_caducitat?: string | null;
  title: string;
  message: string;
  delivery_channel: string;
  delivery_status: string;
  is_read: boolean;
  created_at: string;
}

export interface NotificationSettings {
  notifications_enabled: boolean;
  expiration_notice_days: number;
}

export const notificationService = {
  // Obtenir totes les notificacions de l'usuari
  getNotifications: async (): Promise<NotificationItem[]> => {
    try {
      const response = await apiClient.get("/notifications");
      return response.data?.notifications || [];
    } catch (error: any) {
      throw (
        error.response?.data?.detail || "Error al carregar les notificacions"
      );
    }
  },

  // Marcar com a llegida
  markAsRead: async (id: string): Promise<void> => {
    try {
      await apiClient.patch(`/notifications/${id}/read`);
    } catch (error: any) {
      throw (
        error.response?.data?.detail ||
        "Error al marcar la notificació com a llegida"
      );
    }
  },

  // RF-NOTIF-04: Obtenir la configuració actual
  getSettings: async (): Promise<NotificationSettings> => {
    try {
      const response = await apiClient.get("/notifications/preferences");
      if (response.data.preferences) return response.data.preferences;
      return response.data;
    } catch (error: any) {
      throw error.response?.data?.detail || "Error al carregar la configuració";
    }
  },

  // RF-NOTIF-04: Modificar configuració
  updateSettings: async (
    settings: NotificationSettings,
  ): Promise<NotificationSettings> => {
    try {
      const response = await apiClient.patch(
        "/notifications/preferences",
        settings,
      );
      if (response.data.preferences) return response.data.preferences;
      return response.data;
    } catch (error: any) {
      throw error.response?.data?.detail || "Error al desar la configuració";
    }
  },
};
