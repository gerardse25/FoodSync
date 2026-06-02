import apiClient from "./client";

export type HomeMember = {
  id_usuari: string;
  nom: string;
};

export type HomeData = {
  id_llar?: string;
  nom?: string;
  membres?: HomeMember[];
  members?: HomeMember[];
  home?: {
    id_llar?: string;
    nom?: string;
    membres?: HomeMember[];
    members?: HomeMember[];
  };
  llar?: {
    id_llar?: string;
    nom?: string;
    membres?: HomeMember[];
    members?: HomeMember[];
  };
};

export const homeService = {
  getHome: async (): Promise<HomeData> => {
    try {
      const response = await apiClient.get("/home/");
      return response.data;
    } catch (error: any) {
      throw error.response?.data?.detail || "Error al cargar el hogar";
    }
  },

  createHome: async (name: string) => {
    try {
      const response = await apiClient.post("/home/", { name });
      return response.data;
    } catch (error: any) {
      throw error.response?.data?.detail || "Error al crear el hogar";
    }
  },

  joinHome: async (code: string) => {
    try {
      const response = await apiClient.post("/home/join", {
        invite_code: code,
      });
      return response.data;
    } catch (error: any) {
      throw (
        error.response?.data?.detail || "Error al unirse. Verifica el código."
      );
    }
  },

  getInviteCode: async () => {
    try {
      const response = await apiClient.get("/home/invite-code");
      return response.data;
    } catch (error: any) {
      throw error.response?.data?.detail || "Error al obtener el código";
    }
  },

  regenerateInviteCode: async () => {
    try {
      const response = await apiClient.post("/home/invite-code/regenerate");
      return response.data;
    } catch (error: any) {
      throw error.response?.data?.detail || "Error al generar un nuevo código";
    }
  },

  leaveHome: async () => {
    try {
      const response = await apiClient.delete("/home/leave");
      return response.data;
    } catch (error: any) {
      throw error.response?.data?.detail || "Error al intentar salir del hogar";
    }
  },

  kickMember: async (userId: string) => {
    try {
      const response = await apiClient.delete("/home/kick", {
        data: { user_id: userId },
      });
      return response.data;
    } catch (error: any) {
      throw error.response?.data?.detail || "Error al expulsar al miembro";
    }
  },

  syncHome: async () => {
    try {
      const response = await apiClient.get("/home/sync");
      return response.data;
    } catch (error: any) {
      throw error.response?.data?.detail || "Error al sincronizar";
    }
  },
};