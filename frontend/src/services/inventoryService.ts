import apiClient from "./client";

export interface CreateProductData {
  nom: string;
  categoria: string;
  preu: number;
  quantitat: number;
  data_compra?: string;
  data_caducitat?: string;
  id_propietaris_privats?: string[];
}

export type InventoryOwner = {
  id_usuari: string;
  nom: string;
};

export type NutrientLevelValue = "low" | "moderate" | "high";

export type NutrientLevels = {
  fat?: NutrientLevelValue | null;
  saturated_fat?: NutrientLevelValue | null;
  sugars?: NutrientLevelValue | null;
  salt?: NutrientLevelValue | null;
};

export type Nutriments100g = {
  fat?: number | null;
  saturated_fat?: number | null;
  sugars?: number | null;
  salt?: number | null;
};

export type InventoryProduct = {
  id_producte: string;
  nom: string;
  quantitat: number;
  categoria: string;
  data_caducitat?: string | null;
  es_privat: boolean;
  propietaris: InventoryOwner[];
  nutriscore?: string | null;
  imatge_url?: string | null;
  nutrient_levels?: NutrientLevels | null;
  nutriments_100g?: Nutriments100g | null;
};

export type InventoryCategoryOption = {
  value: string;
  label: string;
};

export type InventoryFilters = {
  search?: string;
  categoria?: string;
  owner_user_id?: string;
  min_quantity?: number;
  max_quantity?: number;
  nutrition_score?: string;
  expiry_filter?: string;
};

export type InventoryNutrition = {
  energy_kcal?: number | null;
  fat?: number | null;
  saturated_fat?: number | null;
  carbohydrates?: number | null;
  sugars?: number | null;
  fiber?: number | null;
  proteins?: number | null;
  salt?: number | null;
  sodium?: number | null;
};

export type InventoryProductDetail = {
  id_producte: string;
  nom: string;
  marca?: string | null;
  quantitat_stock: number;
  quantitat_envas?: string | null;
  categoria?: string | null;
  data_caducitat?: string | null;
  data_caducitat_estimada?: boolean;
  data_compra?: string | null;
  preu?: string | null;
  es_privat: boolean;
  propietaris: InventoryOwner[];
  estat_stock: string;
  nutriscore?: string | null;
  informacio_nutricional_100g_ml?: InventoryNutrition | null;
  ingredients?: string | null;
  allergens?: string | null;
  imatge_url?: string | null;
  nutrient_levels?: NutrientLevels | null;
  nutriments_100g?: Nutriments100g | null;
};

export type EstimateExpirationPayload = {
  categoria: string;
  data_compra?: string | null;
};

export type EstimateExpirationResponse = {
  code?: string;
  categoria: string;
  dies_caducitat_estimats: number;
  data_compra: string;
  data_caducitat: string;
  data_caducitat_estimada: boolean;
};

export const inventoryService = {
  createManualProduct: async (productData: CreateProductData) => {
    try {
      const response = await apiClient.post("/inventory/manual", productData);
      return response.data;
    } catch (error: any) {
      throw error.response?.data?.detail || "Error al afegir el producte";
    }
  },

  getInventoryProducts: async (
    filters: InventoryFilters = {},
  ): Promise<InventoryProduct[]> => {
    try {
      const response = await apiClient.get("/inventory", {
        params: {
          search: filters.search?.trim() || undefined,
          categoria: filters.categoria || undefined,
          owner_user_id: filters.owner_user_id || undefined,
          min_quantity: filters.min_quantity,
          max_quantity: filters.max_quantity,
          nutrition_score: filters.nutrition_score || undefined,
          expiry_filter: filters.expiry_filter || undefined,
        },
      });

      return response.data?.productes || response.data?.products || [];
    } catch (error: any) {
      throw (
        error.response?.data?.detail || "No s'ha pogut carregar l'inventari"
      );
    }
  },

  getCategories: async (): Promise<InventoryCategoryOption[]> => {
    try {
      const response = await apiClient.get("/inventory/categories/all");

      if (Array.isArray(response.data)) {
        return response.data;
      }

      if (Array.isArray(response.data?.categories)) {
        return response.data.categories;
      }

      return [];
    } catch {
      return [];
    }
  },

  getInventoryProductDetail: async (
    productId: string,
  ): Promise<InventoryProductDetail> => {
    try {
      const response = await apiClient.get(`/inventory/${productId}`);
      return response.data?.producte;
    } catch (error: any) {
      throw (
        error.response?.data?.detail || "No s'ha pogut carregar el producte"
      );
    }
  },

  updateProductQuantity: async (id_producte: string, modificacio: number) => {
    try {
      const response = await apiClient.patch("/inventory_modify", {
        id_producte,
        modificacio,
      });
      return response.data;
    } catch (error: any) {
      throw (
        error.response?.data?.detail || "No s'ha pogut modificar la quantitat"
      );
    }
  },

  updateProductOwners: async (
    id_producte: string,
    data: { id_producte: string; owner_user_ids: string[] },
  ) => {
    try {
      const response = await apiClient.patch("/inventory/owners", data);
      return response.data;
    } catch (error: any) {
      throw (
        error.response?.data?.detail || "Error al actualitzar els propietaris"
      );
    }
  },

  updateProduct: async (
    id_producte: string,
    productData: {
      nom?: string;
      categoria?: string;
      preu?: number | null;
      data_caducitat?: string | null;
    },
  ) => {
    try {
      const response = await apiClient.patch(
        `/inventory_modify/${id_producte}`,
        productData,
      );
      return response.data;
    } catch (error: any) {
      throw error.response?.data?.detail || "Error al modificar el producte";
    }
  },

  deleteProduct: async (id_producte: string) => {
    try {
      const response = await apiClient.delete("/inventory_delete_product", {
        data: { id_producte },
      });
      return response.data;
    } catch (error: any) {
      throw (
        error.response?.data?.detail || "No s'ha pogut eliminar el producte"
      );
    }
  },

  getBarcodeProductSummary: async (barcode: string) => {
    try {
      const response = await apiClient.get(`/inventory/barcode/${barcode}`);
      return response.data;
    } catch (error: any) {
      throw (
        error.response?.data?.error ||
        error.response?.data?.detail ||
        "Error al buscar el codi de barres"
      );
    }
  },

  lookupBarcode: async (barcode: string) => {
    try {
      const response = await apiClient.get(`/inventory/barcode/${barcode}`);
      return response.data;
    } catch (error: any) {
      throw (
        error.response?.data?.error ||
        error.response?.data?.detail ||
        "Error al buscar el codi de barres"
      );
    }
  },

  confirmBarcodeProduct: async (productData: any) => {
    try {
      const response = await apiClient.post(
        "/inventory/barcode/confirm",
        productData,
      );
      return response.data;
    } catch (error: any) {
      throw (
        error.response?.data?.error ||
        error.response?.data?.detail ||
        "Error al guardar el producte escanejat"
      );
    }
  },

  estimateExpiration: async (
    payload: EstimateExpirationPayload,
  ): Promise<EstimateExpirationResponse> => {
    try {
      const response = await apiClient.post(
        "/inventory/expiration/estimate",
        payload,
      );
      return response.data;
    } catch (error: any) {
      throw (
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        "No s'ha pogut estimar la data de caducitat"
      );
    }
  },

  processReceiptOCR: async (imageUri: string) => {
    try {
      const formData = new FormData();

      formData.append("file", {
        uri: imageUri,
        name: "ticket.jpg",
        type: "image/jpeg",
      } as any);

      const response = await apiClient.post("/inventory/ticket/ocr", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      return response.data;
    } catch (error: any) {
      throw (
        error.response?.data?.detail ||
        error.response?.data?.error ||
        "Error al processar el tiquet"
      );
    }
  },

  confirmReceiptTicket: async (products: any[]) => {
    try {
      const response = await apiClient.post("/inventory/ticket/confirm", {
        productes: products,
      });
      return response.data;
    } catch (error: any) {
      throw (
        error.response?.data?.error ||
        error.response?.data?.detail ||
        "Error al confirmar els productes del tiquet"
      );
    }
  },
};
