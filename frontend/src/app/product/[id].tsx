import { router, useLocalSearchParams } from "expo-router";
import {
  ArrowLeft,
  CircleAlert,
  Edit3,
  Lock,
  MoreVertical,
  Package,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Tag,
  Trash2,
  X,
} from "lucide-react-native";
import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { authService } from "../../services/authService";
import {
  inventoryService,
  type InventoryProductDetail,
} from "../../services/inventoryService";
import { shoppingListService } from "../../services/shoppingListService";

const LEVEL_STYLES = {
  low: {
    dot: "#52E000",
    text: "text-emerald-700",
    label: "Quantitat baixa",
  },
  moderate: {
    dot: "#FACC15",
    text: "text-amber-600",
    label: "Quantitat moderada",
  },
  high: {
    dot: "#EF4444",
    text: "text-red-500",
    label: "Quantitat elevada",
  },
} as const;

const NUTRIENT_ROWS = [
  { key: "fat", label: "Greixos" },
  { key: "saturated_fat", label: "Greixos saturats" },
  { key: "sugars", label: "Sucres" },
  { key: "salt", label: "Sal" },
] as const;

type NutrientKey = (typeof NUTRIENT_ROWS)[number]["key"];

function getNutrientLevelMeta(level?: string | null) {
  if (level === "low") return LEVEL_STYLES.low;
  if (level === "moderate") return LEVEL_STYLES.moderate;
  if (level === "high") return LEVEL_STYLES.high;

  return {
    dot: "#D1D5DB",
    text: "text-gray-500",
    label: "Sense dades",
  };
}

function formatPer100g(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return null;
  }

  return `${value}g`;
}

export default function ProductDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();

  const [product, setProduct] = useState<InventoryProductDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [currentUserId, setCurrentUserId] = useState<string | null>(null);

  const [updatingQuantity, setUpdatingQuantity] = useState(false);
  const [deletingProduct, setDeletingProduct] = useState(false);

  const [isMenuVisible, setIsMenuVisible] = useState(false);

  const fetchCurrentUser = async () => {
    try {
      const result = await authService.verify();
      const userId =
        result?.user?.id ||
        result?.user?.id_usuari ||
        result?.user?.user_id ||
        result?.id ||
        null;

      setCurrentUserId(userId ? String(userId) : null);
    } catch {
      setCurrentUserId(null);
    }
  };

  const fetchProduct = async (showLoader = true) => {
    try {
      if (!id) return;

      if (showLoader) setLoading(true);
      setError("");

      const data = await inventoryService.getInventoryProductDetail(String(id));
      setProduct(data);
    } catch (err: any) {
      setError(
        typeof err === "string" ? err : "No s'ha pogut carregar el producte",
      );
    } finally {
      if (showLoader) setLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentUser();
    fetchProduct(true);
  }, [id]);

  const canEditProduct = useMemo(() => {
    if (!product) return false;
    if (!product.es_privat) return true;
    if (!currentUserId) return false;

    return product.propietaris.some(
      (owner) => String(owner.id_usuari) === String(currentUserId),
    );
  }, [product, currentUserId]);

  const isReadOnlyPrivate = !!product?.es_privat && !canEditProduct;

  const handleUpdateQuantity = async (delta: number) => {
    if (!product || updatingQuantity || deletingProduct || !canEditProduct) {
      return;
    }

    const currentQuantity = product.quantitat_stock ?? 0;
    const newQuantity = currentQuantity + delta;

    if (newQuantity < 0) return;

    const previousQuantity = currentQuantity;

    setProduct((prev) =>
      prev
        ? {
            ...prev,
            quantitat_stock: newQuantity,
          }
        : prev,
    );

    try {
      setUpdatingQuantity(true);
      await inventoryService.updateProductQuantity(
        String(product.id_producte),
        delta,
      );
      await fetchProduct(false);
    } catch (err: any) {
      setProduct((prev) =>
        prev
          ? {
              ...prev,
              quantitat_stock: previousQuantity,
            }
          : prev,
      );

      Alert.alert(
        "Error",
        typeof err === "string"
          ? err
          : "No s'ha pogut actualitzar la quantitat",
      );
    } finally {
      setUpdatingQuantity(false);
    }
  };

  const handleDeleteProduct = () => {
    if (!product || deletingProduct || !canEditProduct) return;

    Alert.alert(
      "Eliminar producte",
      `Segur que vols eliminar "${product.nom}" de l'inventari?`,
      [
        {
          text: "Cancel·lar",
          style: "cancel",
        },
        {
          text: "Eliminar",
          style: "destructive",
          onPress: async () => {
            try {
              setDeletingProduct(true);
              await inventoryService.deleteProduct(String(product.id_producte));

              Alert.alert(
                "Producte eliminat",
                "El producte s'ha eliminat correctament.",
                [
                  {
                    text: "OK",
                    onPress: () => router.back(),
                  },
                ],
              );
            } catch (err: any) {
              Alert.alert(
                "Error",
                typeof err === "string"
                  ? err
                  : "No s'ha pogut eliminar el producte",
              );
            } finally {
              setDeletingProduct(false);
            }
          },
        },
      ],
    );
  };

  const handleAddToShoppingList = () => {
    if (!product) return;

    Alert.alert(
      "Afegir a la llista",
      `Vols afegir "${product.nom}" a la llista de la compra?`,
      [
        { text: "Cancel·lar", style: "cancel" },
        {
          text: "Afegir ",
          onPress: async () => {
            await shoppingListService.addItem({
              nom: product.nom,
              quantitat: 1,
              categoria: product.categoria || null,
              source: "product_detail",
              originalProductId: product.id_producte,
            });

            Alert.alert("Afegit", "Producte afegit a la llista de la compra.");
          },
        },
      ],
    );
  };

  const InfoRow = ({
    label,
    value,
    extra,
  }: {
    label: string;
    value?: string | number | null;
    extra?: React.ReactNode;
  }) => (
    <View className="py-3 border-b border-gray-100">
      <Text className="text-xs uppercase tracking-wide text-gray-500 mb-1">
        {label}
      </Text>

      <Text className="text-base text-gray-900">
        {value !== null && value !== undefined && value !== ""
          ? String(value)
          : "No disponible"}
      </Text>

      {extra ? <View className="mt-2">{extra}</View> : null}
    </View>
  );

  const NutriRow = ({
    label,
    value,
  }: {
    label: string;
    value?: string | number | null;
  }) => {
    const hasValue = value !== null && value !== undefined && value !== "";

    return (
      <View className="w-[48%] px-4 py-3 border-b border-gray-100">
        <Text className="text-[11px] uppercase tracking-wide text-gray-500 mb-1">
          {label}
        </Text>

        <Text
          className={`text-sm font-bold ${
            hasValue ? "text-gray-900" : "text-gray-400"
          }`}
        >
          {hasValue ? String(value) : "No disponible"}
        </Text>
      </View>
    );
  };

  const ownersText =
    product?.propietaris && product.propietaris.length > 0
      ? product.propietaris.map((owner) => owner.nom).join(", ")
      : "El producte es compartit";

  return (
    <SafeAreaView className="flex-1 bg-white">
      <View className="px-4 pt-4 pb-2 flex-row justify-between items-center bg-white z-10">
        <TouchableOpacity
          className="w-10 h-10 rounded-xl items-center justify-center"
          onPress={() => router.back()}
        >
          <ArrowLeft color="#1F2937" size={24} />
        </TouchableOpacity>
        <Text className="font-bold text-lg">Detalls del producte</Text>
        {canEditProduct ? (
          <TouchableOpacity
            onPress={() => setIsMenuVisible(true)}
            className="p-2"
          >
            <MoreVertical size={24} color="#1F2937" />
          </TouchableOpacity>
        ) : (
          <View className="w-10" />
        )}
      </View>

      {loading ? (
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator size="large" color="#10B981" />
          <Text className="text-gray-500 mt-4">Carregant producte...</Text>
        </View>
      ) : error || !product ? (
        <View className="flex-1 items-center justify-center px-6">
          <CircleAlert color="#EF4444" size={28} />
          <Text className="text-red-500 text-center font-medium mt-3">
            {error || "No s'ha pogut carregar el producte"}
          </Text>

          <TouchableOpacity
            className="mt-4 bg-emerald-500 px-5 py-3 rounded-xl"
            onPress={() => fetchProduct(true)}
          >
            <Text className="text-white font-semibold">Reintentar</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <ScrollView
          className="flex-1"
          contentContainerStyle={{ paddingBottom: 40 }}
          showsVerticalScrollIndicator={false}
        >
          <View className="w-full h-72 bg-gray-100 relative">
            {product.imatge_url ? (
              <Image
                source={{ uri: product.imatge_url }}
                className="w-full h-full"
                resizeMode="contain"
              />
            ) : (
              <View className="flex-1 items-center justify-center">
                <Package size={60} color="#9CA3AF" />
              </View>
            )}
            {product.nutriscore ? (
              <View className="absolute top-4 right-4 bg-emerald-600 px-4 py-2 rounded-xl">
                <Text className="text-white font-bold text-xl">
                  {product.nutriscore}
                </Text>
              </View>
            ) : null}
          </View>

          <View className="px-6 py-6 -mt-6 bg-white rounded-t-[32px]">
            <View>
              <Text className="text-2xl font-bold text-gray-900">
                {product.nom}
              </Text>

              <Text className="text-sm text-gray-500 mt-1">
                {product.marca || "Marca no disponible"}
              </Text>

              <View className="flex-row flex-wrap mt-3 gap-2">
                <View className="mt-4 self-start bg-red-50 px-4 py-1.5 rounded-full flex-row items-center border border-red-100">
                  <CircleAlert color="#d90606" size={14} />
                  <Text className="text-red-800 font-bold text-sm pl-2">
                    Caduca el {product.data_caducitat || "?"}
                  </Text>
                </View>

                <View className="bg-green-50 self-start rounded-full px-4 py-1.5 border border-green-100">
                  <Text className="text-green-700 font-medium">
                    Stock: {product.quantitat_stock}
                  </Text>
                </View>
              </View>
            </View>

            {isReadOnlyPrivate ? (
              <View>
                <View className="flex-row items-start bg-amber-50 border border-amber-200 rounded-2xl px-4 py-3 mb-6">
                  <Lock color="#D97706" size={18} />
                  <View className="ml-3 flex-1">
                    <Text className="text-amber-800 font-semibold">
                      Producte privat en mode lectura
                    </Text>
                    <Text className="text-amber-700 mt-1">
                      Pots consultar la informació, però no modificar la
                      quantitat ni eliminar el producte perquè pertany a un
                      altre usuari.
                    </Text>
                  </View>
                </View>
              </View>
            ) : null}

            {!isReadOnlyPrivate ? (
              <View className="bg-gray-100 p-4 rounded-3xl border border-gray-100 mb-4 flex-row justify-between items-center">
                <View>
                  <Text className="font-bold text-base text-gray-900">
                    Quantitat
                  </Text>
                  <Text className="text-sm text-gray-500 pt-3">
                    Ajusta l&apos;estoc actual
                  </Text>
                </View>

                <View className="flex-row items-center gap-4">
                  <TouchableOpacity
                    onPress={() => handleUpdateQuantity(-1)}
                    className="w-10 h-10 bg-white rounded-xl items-center justify-center"
                  >
                    <Text className="font-bold text-xl">-</Text>
                  </TouchableOpacity>

                  <Text className="font-bold text-xl w-6 text-center">
                    {product.quantitat_stock}
                  </Text>

                  <TouchableOpacity
                    onPress={() => handleUpdateQuantity(1)}
                    className="w-10 h-10 bg-emerald-500 rounded-xl items-center justify-center"
                  >
                    <Text className="font-bold text-xl text-white">+</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ) : null}

            <View className="mt-4 mb-2">
              <TouchableOpacity
                className="bg-emerald-500 rounded-2xl h-14 flex-row items-center justify-center"
                onPress={handleAddToShoppingList}
              >
                <ShoppingCart color="#FFFFFF" size={18} />
                <Text className="text-white font-bold text-base ml-2">
                  Afegir a la llista
                </Text>
              </TouchableOpacity>
            </View>

            <View className="bg-white rounded-3xl">
              <Text className="text-lg font-bold text-gray-900 mb-2">
                Informació general
              </Text>

              <InfoRow label="Categoria" value={product.categoria} />
              <InfoRow
                label="Quantitat envàs"
                value={product.quantitat_envas}
              />
              <InfoRow label="Data de compra" value={product.data_compra} />
              <InfoRow
                label="Data de caducitat"
                value={product.data_caducitat}
                extra={
                  product.data_caducitat_estimada ? (
                    <View className="self-start flex-row items-center bg-emerald-50 border border-emerald-200 rounded-full px-3 py-1">
                      <Sparkles color="#10B981" size={14} />
                      <Text className="ml-2 text-emerald-700 text-xs font-semibold">
                        Data estimada automàticament
                      </Text>
                    </View>
                  ) : null
                }
              />
              <InfoRow label="Preu" value={product.preu} />
            </View>

            <View className="bg-white rounded-3xl pt-6">
              <Text className="text-lg font-bold text-gray-900 mb-2">
                Privacitat del producte
              </Text>

              <View className="flex-row items-center mb-3">
                <ShieldCheck
                  color={product.es_privat ? "#D97706" : "#10B981"}
                  size={18}
                />
                <Text className="ml-2 text-base text-gray-900">
                  {product.es_privat ? "Producte privat" : "Producte compartit"}
                </Text>
              </View>

              {product.es_privat ? (
                <View className="flex-row items-start">
                  <Tag color="#6B7280" size={18} />
                  <Text className="ml-2 text-base text-gray-900 flex-1">
                    {ownersText}
                  </Text>
                </View>
              ) : null}
            </View>

            <View className="bg-white rounded-3xl mt-2">
              <Text className="text-lg font-bold text-gray-900 mb-4">
                Valors nutricionals
              </Text>

              {NUTRIENT_ROWS.map(({ key, label }) => {
                const level = product.nutrient_levels?.[key as NutrientKey];
                const value = product.nutriments_100g?.[key as NutrientKey];
                const meta = getNutrientLevelMeta(level);
                const formattedValue = formatPer100g(value);

                return (
                  <View
                    key={key}
                    className="flex-row items-center py-3 border-b border-gray-100 last:border-b-0"
                  >
                    <View
                      className="w-5 h-5 rounded-full mr-4"
                      style={{ backgroundColor: meta.dot }}
                    />
                    <Text className={`flex-1 text-base ${meta.text}`}>
                      {level
                        ? `${label} en ${meta.label.toLowerCase()}${
                            formattedValue ? ` (${formattedValue})` : ""
                          }`
                        : `${label}: sense dades`}
                    </Text>
                  </View>
                );
              })}
            </View>

            <View className="bg-white rounded-3xl mt-4">
              <Text className="text-lg font-bold text-gray-900 mb-2">
                Ingredients
              </Text>
              <Text className="text-base text-gray-700">
                {product.ingredients || "No disponible"}
              </Text>
            </View>

            <View className="bg-white rounded-3xl mt-4">
              <Text className="text-lg font-bold text-gray-900 mb-2">
                Al·lèrgens
              </Text>
              <Text className="text-base text-gray-700">
                {product.allergens || "No disponible"}
              </Text>
            </View>

            <View className="mt-4">
              <View className="bg-white rounded-3xl">
                <Text className="text-lg font-bold text-gray-900 mb-4">
                  Informació nutricional (100g/ml)
                </Text>

                {!product.informacio_nutricional_100g_ml ? (
                  <Text className="text-gray-500 text-center">
                    No hi ha informació nutricional disponible.
                  </Text>
                ) : (
                  <View className="flex-row flex-wrap justify-between gap-y-3">
                    <NutriRow
                      label="Energia (kcal)"
                      value={
                        product.informacio_nutricional_100g_ml?.energy_kcal
                      }
                    />
                    <NutriRow
                      label="Greixos"
                      value={product.informacio_nutricional_100g_ml?.fat}
                    />
                    <NutriRow
                      label="Greixos saturats"
                      value={
                        product.informacio_nutricional_100g_ml?.saturated_fat
                      }
                    />
                    <NutriRow
                      label="Hidrats de carboni"
                      value={
                        product.informacio_nutricional_100g_ml?.carbohydrates
                      }
                    />
                    <NutriRow
                      label="Sucres"
                      value={product.informacio_nutricional_100g_ml?.sugars}
                    />
                    <NutriRow
                      label="Fibra"
                      value={product.informacio_nutricional_100g_ml?.fiber}
                    />
                    <NutriRow
                      label="Proteïnes"
                      value={product.informacio_nutricional_100g_ml?.proteins}
                    />
                    <NutriRow
                      label="Sal"
                      value={product.informacio_nutricional_100g_ml?.salt}
                    />
                    <NutriRow
                      label="Sodi"
                      value={product.informacio_nutricional_100g_ml?.sodium}
                    />
                  </View>
                )}
              </View>
            </View>
          </View>
        </ScrollView>
      )}

      {isMenuVisible ? (
        <View className="absolute inset-0 bg-black/50 justify-end z-50">
          <TouchableOpacity
            className="flex-1"
            onPress={() => setIsMenuVisible(false)}
          />
          <View className="bg-white rounded-t-3xl px-6 pt-6 pb-10">
            <View className="flex-row justify-between items-center mb-6">
              <Text className="text-xl font-bold text-gray-900">Opcions</Text>
              <TouchableOpacity
                onPress={() => setIsMenuVisible(false)}
                className="p-2 bg-gray-100 rounded-full"
              >
                <X color="#4B5563" size={20} />
              </TouchableOpacity>
            </View>

            <TouchableOpacity
              className="flex-row items-center p-4 bg-gray-50 rounded-2xl mb-3"
              onPress={() => {
                if (!product) return;
                setIsMenuVisible(false);
                const editPayload = {
                  id_producte: product.id_producte,
                  nom: product.nom,
                  categoria: product.categoria,
                  price: product.preu ? String(product.preu) : "",
                  quantity: product.quantitat_stock
                    ? String(product.quantitat_stock)
                    : "1",
                  purchaseDate: product.data_compra,
                  expirationDate: product.data_caducitat,
                  isPrivate: product.es_privat,
                  isEstimatedExpiration: product.data_caducitat_estimada,
                };
                router.push({
                  pathname: "/(tabs)/products/addManualProducts",
                  params: { prefill: JSON.stringify(editPayload) },
                });
              }}
            >
              <Edit3 size={20} color="#10B981" />
              <Text className="ml-3 font-bold text-gray-900">
                Editar producte
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              className="flex-row items-center p-4 bg-red-50 rounded-2xl"
              onPress={() => {
                setIsMenuVisible(false);
                handleDeleteProduct();
              }}
            >
              <Trash2 size={20} color="#EF4444" />
              <Text className="ml-3 font-bold text-red-600">
                Eliminar producte
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      ) : null}
    </SafeAreaView>
  );
}
