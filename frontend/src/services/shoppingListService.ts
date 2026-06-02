import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

export type ShoppingListItem = {
  id: string;
  nom: string;
  quantitat: number;
  categoria?: string | null;
  addedAt: string;
  source: "inventory" | "product_detail" | "expired_product" | "manual";
  originalProductId?: string | null;
  checked: boolean;
};

const STORAGE_KEY = "shopping_list_items";

const getStoredValue = async () => {
  if (Platform.OS === "web") {
    return localStorage.getItem(STORAGE_KEY);
  }
  return await SecureStore.getItemAsync(STORAGE_KEY);
};

const setStoredValue = async (value: string) => {
  if (Platform.OS === "web") {
    localStorage.setItem(STORAGE_KEY, value);
  } else {
    await SecureStore.setItemAsync(STORAGE_KEY, value);
  }
};

export const shoppingListService = {
  getItems: async (): Promise<ShoppingListItem[]> => {
    try {
      const raw = await getStoredValue();
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  },

  saveItems: async (items: ShoppingListItem[]) => {
    await setStoredValue(JSON.stringify(items));
  },

  addItem: async (
    item: Omit<ShoppingListItem, "id" | "addedAt" | "checked">
  ): Promise<ShoppingListItem[]> => {
    const currentItems = await shoppingListService.getItems();

    const existingIndex = currentItems.findIndex(
      (existing) =>
        existing.nom.trim().toLowerCase() === item.nom.trim().toLowerCase()
    );

    if (existingIndex >= 0) {
      currentItems[existingIndex] = {
        ...currentItems[existingIndex],
        quantitat: currentItems[existingIndex].quantitat + item.quantitat,
        categoria: item.categoria ?? currentItems[existingIndex].categoria,
        originalProductId:
          item.originalProductId ?? currentItems[existingIndex].originalProductId,
      };
      await shoppingListService.saveItems(currentItems);
      return currentItems;
    }

    const newItem: ShoppingListItem = {
      ...item,
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      addedAt: new Date().toISOString(),
      checked: false,
    };

    const updatedItems = [newItem, ...currentItems];
    await shoppingListService.saveItems(updatedItems);
    return updatedItems;
  },

  updateQuantity: async (
    id: string,
    quantitat: number
  ): Promise<ShoppingListItem[]> => {
    const currentItems = await shoppingListService.getItems();

    const updatedItems = currentItems.map((item) =>
      item.id === id ? { ...item, quantitat: Math.max(1, quantitat) } : item
    );

    await shoppingListService.saveItems(updatedItems);
    return updatedItems;
  },

  toggleItem: async (id: string): Promise<ShoppingListItem[]> => {
    const currentItems = await shoppingListService.getItems();

    const updatedItems = currentItems.map((item) =>
      item.id === id ? { ...item, checked: !item.checked } : item
    );

    await shoppingListService.saveItems(updatedItems);
    return updatedItems;
  },

  removeItem: async (id: string): Promise<ShoppingListItem[]> => {
    const currentItems = await shoppingListService.getItems();
    const updatedItems = currentItems.filter((item) => item.id !== id);
    await shoppingListService.saveItems(updatedItems);
    return updatedItems;
  },

  clearCheckedItems: async (): Promise<ShoppingListItem[]> => {
    const currentItems = await shoppingListService.getItems();
    const updatedItems = currentItems.filter((item) => !item.checked);
    await shoppingListService.saveItems(updatedItems);
    return updatedItems;
  },
};