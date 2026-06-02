import {
  inventoryService,
  type InventoryCategoryOption,
} from "@/src/services/inventoryService";
import {
  shoppingListService,
  type ShoppingListItem,
} from "@/src/services/shoppingListService";
import { useFocusEffect } from "expo-router";
import { Check, Plus, ShoppingCart, Trash2 } from "lucide-react-native";
import React, { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

function getTodayDate() {
  return new Date().toISOString().split("T")[0];
}

export default function ShoppingListScreen() {
  const [items, setItems] = useState<ShoppingListItem[]>([]);
  const [categories, setCategories] = useState<InventoryCategoryOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [movingItemId, setMovingItemId] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [itemsData, categoriesData] = await Promise.all([
        shoppingListService.getItems(),
        inventoryService.getCategories(),
      ]);

      setItems(itemsData);
      setCategories(categoriesData || []);
    } finally {
      setIsLoading(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadData();
    }, []),
  );

  const pendingItems = useMemo(
    () => items.filter((item) => !item.checked),
    [items],
  );

  const completedItems = useMemo(
    () => items.filter((item) => item.checked),
    [items],
  );

  const resolveCategoryValue = (item: ShoppingListItem) => {
    const raw = item.categoria?.trim();

    if (!raw) return "OTHER";

    const exactValueMatch = categories.find(
      (cat) => cat.value.trim().toLowerCase() === raw.toLowerCase(),
    );
    if (exactValueMatch) return exactValueMatch.value;

    const exactLabelMatch = categories.find(
      (cat) => cat.label.trim().toLowerCase() === raw.toLowerCase(),
    );
    if (exactLabelMatch) return exactLabelMatch.value;

    return "OTHER";
  };

  const moveItemToInventory = async (item: ShoppingListItem) => {
    await inventoryService.createManualProduct({
      nom: item.nom.trim(),
      categoria: resolveCategoryValue(item),
      preu: 0,
      quantitat: Math.max(1, item.quantitat),
      data_compra: getTodayDate(),
    });
  };

  const handleToggle = async (item: ShoppingListItem) => {
    if (!item.checked) {
      Alert.alert(
        "Marcar com comprat",
        "Vols marcar aquest producte com a comprat?",
        [
          { text: "Cancel·lar", style: "cancel" },
          {
            text: "Sí",
            onPress: async () => {
              Alert.alert(
                "Passar a l'inventari",
                "Vols moure automàticament aquest producte a l'inventari?",
                [
                  {
                    text: "Ara no",
                    style: "cancel",
                    onPress: async () => {
                      const updated = await shoppingListService.toggleItem(
                        item.id,
                      );
                      setItems(updated);
                    },
                  },
                  {
                    text: "D'acord",
                    onPress: async () => {
                      try {
                        setMovingItemId(item.id);
                        await moveItemToInventory(item);

                        const updated = await shoppingListService.toggleItem(
                          item.id,
                        );
                        setItems(updated);

                        Alert.alert(
                          "Afegit a l'inventari",
                          "El producte s'ha afegit correctament a l'inventari.",
                        );
                      } catch (error: any) {
                        Alert.alert(
                          "Error",
                          typeof error === "string"
                            ? error
                            : "No s'ha pogut afegir el producte a l'inventari.",
                        );
                      } finally {
                        setMovingItemId(null);
                      }
                    },
                  },
                ],
              );
            },
          },
        ],
      );
      return;
    }

    const updated = await shoppingListService.toggleItem(item.id);
    setItems(updated);
  };

  const handleRemove = async (id: string) => {
    const updated = await shoppingListService.removeItem(id);
    setItems(updated);
  };

  const handleIncrease = async (item: ShoppingListItem) => {
    const updated = await shoppingListService.updateQuantity(
      item.id,
      item.quantitat + 1,
    );
    setItems(updated);
  };

  const handleDecrease = async (item: ShoppingListItem) => {
    const updated = await shoppingListService.updateQuantity(
      item.id,
      Math.max(1, item.quantitat - 1),
    );
    setItems(updated);
  };

  const handleClearChecked = () => {
    Alert.alert(
      "Eliminar comprats",
      "Vols eliminar tots els productes marcats com a comprats?",
      [
        { text: "Cancel·lar", style: "cancel" },
        {
          text: "Eliminar",
          style: "destructive",
          onPress: async () => {
            const updated = await shoppingListService.clearCheckedItems();
            setItems(updated);
          },
        },
      ],
    );
  };

  if (isLoading) {
    return (
      <SafeAreaView className="flex-1 bg-[#F8FAF8] justify-center items-center">
        <ActivityIndicator size="large" color="#10B981" />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-[#F8FAF8]">
      <View className="px-6 pt-6 pb-4 bg-white border-b border-gray-200">
        <Text className="text-2xl font-bold text-gray-900">Llista compra</Text>
        <Text className="text-sm text-gray-500 mt-1">
          Afegeix, edita, elimina i marca productes com a comprats
        </Text>
      </View>

      <ScrollView
        className="flex-1 px-6 pt-6"
        contentContainerStyle={{ paddingBottom: 40 }}
        showsVerticalScrollIndicator={false}
      >
        <View className="bg-emerald-50 border border-emerald-100 rounded-3xl p-5 mb-6">
          <Text className="text-emerald-700 font-semibold text-base">
            Pendents: {pendingItems.length}
          </Text>
          <Text className="text-emerald-700 font-semibold text-base mt-1">
            Comprats: {completedItems.length}
          </Text>
        </View>

        {items.length === 0 ? (
          <View className="bg-white rounded-3xl p-8 border border-gray-100 items-center">
            <ShoppingCart color="#9CA3AF" size={44} />
            <Text className="text-lg font-bold text-gray-900 mt-4">
              La llista està buida
            </Text>
            <Text className="text-gray-500 text-center mt-2">
              Pots afegir productes des de l&apos;inventari o des del detall del
              producte.
            </Text>
          </View>
        ) : (
          <>
            {pendingItems.map((item) => (
              <View
                key={item.id}
                className="bg-white rounded-[18px] px-4 py-2.5 border border-gray-100 shadow-sm mb-3"
              >
                <View className="flex-row items-start">
                  <TouchableOpacity
                    className="w-10 h-10 rounded-full border-[2.5px] border-emerald-500 items-center justify-center mr-3 mt-0.5"
                    onPress={() => handleToggle(item)}
                    disabled={movingItemId === item.id}
                  >
                    {movingItemId === item.id ? (
                      <ActivityIndicator size="small" color="#10B981" />
                    ) : item.checked ? (
                      <Check color="#10B981" size={15} />
                    ) : null}
                  </TouchableOpacity>

                  <View className="flex-1 min-w-0">
                    <View className="flex-row items-start justify-between">
                      <View className="flex-1 pr-2">
                        <Text className="text-[15px] font-bold text-gray-900">
                          {item.nom}
                        </Text>

                        <Text className="text-[13px] text-gray-500 mt-0.5">
                          {item.categoria || "Sense categoria"}
                        </Text>
                      </View>

                      <TouchableOpacity
                        className="w-9 h-9 rounded-full bg-red-50 items-center justify-center ml-2"
                        onPress={() => handleRemove(item.id)}
                      >
                        <Trash2 color="#EF4444" size={15} />
                      </TouchableOpacity>
                    </View>

                    <View className="flex-row items-center justify-end mt-2.5">
                      <TouchableOpacity
                        className="w-9 h-9 rounded-xl bg-gray-100 items-center justify-center"
                        onPress={() => handleDecrease(item)}
                      >
                        <Text className="text-base font-bold text-gray-900">
                          -
                        </Text>
                      </TouchableOpacity>

                      <Text className="mx-3 text-base font-bold text-gray-900 min-w-[18px] text-center">
                        {item.quantitat}
                      </Text>

                      <TouchableOpacity
                        className="w-9 h-9 rounded-xl bg-emerald-500 items-center justify-center"
                        onPress={() => handleIncrease(item)}
                      >
                        <Plus color="#FFFFFF" size={15} />
                      </TouchableOpacity>
                    </View>
                  </View>
                </View>
              </View>
            ))}

            {completedItems.length > 0 && (
              <>
                <View className="flex-row items-center justify-between mt-4 mb-4">
                  <Text className="text-2xl font-bold text-gray-900">
                    Comprats
                  </Text>
                  <TouchableOpacity onPress={handleClearChecked}>
                    <Text className="text-red-500 font-semibold text-lg">
                      Eliminar marcats
                    </Text>
                  </TouchableOpacity>
                </View>

                {completedItems.map((item) => (
                  <View
                    key={item.id}
                    className="bg-gray-50 rounded-[18px] px-4 py-2.5 border border-gray-200 mb-3"
                  >
                    <View className="flex-row items-center">
                      <TouchableOpacity
                        className="w-10 h-10 rounded-full bg-emerald-500 items-center justify-center mr-3"
                        onPress={() => handleToggle(item)}
                      >
                        <Check color="#FFFFFF" size={15} />
                      </TouchableOpacity>

                      <View className="flex-1 min-w-0">
                        <View className="flex-row items-start justify-between">
                          <View className="flex-1 pr-2">
                            <Text className="text-[15px] font-bold text-gray-500 line-through">
                              {item.nom}
                            </Text>
                            <Text className="text-[13px] text-gray-400 mt-0.5">
                              Quantitat: {item.quantitat}
                            </Text>
                          </View>

                          <TouchableOpacity
                            className="w-9 h-9 rounded-full bg-red-50 items-center justify-center ml-2"
                            onPress={() => handleRemove(item.id)}
                          >
                            <Trash2 color="#EF4444" size={15} />
                          </TouchableOpacity>
                        </View>
                      </View>
                    </View>
                  </View>
                ))}
              </>
            )}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}