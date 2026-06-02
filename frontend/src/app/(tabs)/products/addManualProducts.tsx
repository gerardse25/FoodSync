import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import {
  ArrowLeft,
  CheckSquare,
  ChevronDown,
  Lock,
  Sparkles,
  Square,
  Unlock,
} from "lucide-react-native";
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-aware-scroll-view";
import { SafeAreaView } from "react-native-safe-area-context";

import DatePickerField from "../../../components/products/DatePickerField";
import SearchablePicker from "../../../components/products/SearchablePicker";
import { useAuth } from "../../../context/AuthContext";
import { inventoryService } from "../../../services/inventoryService";

export default function AddManualProductScreen() {
  const { prefill } = useLocalSearchParams();
  const { session } = useAuth();

  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [purchaseDate, setPurchaseDate] = useState<Date | null>(new Date());
  const [expirationDate, setExpirationDate] = useState<Date | null>(null);
  const [isPrivate, setIsPrivate] = useState(false);
  const [barcode, setBarcode] = useState<string | null>(null);
  const [productId, setProductId] = useState<string | null>(null);
  const [isBoughtToday, setIsBoughtToday] = useState(false);

  const [categories, setCategories] = useState<
    { label: string; value: string }[]
  >([]);
  const [selectedCategory, setSelectedCategory] = useState<{
    label: string;
    value: string;
  } | null>(null);
  const [isPickerVisible, setIsPickerVisible] = useState(false);

  const [isLoadingCategories, setIsLoadingCategories] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [isEstimatingExpiration, setIsEstimatingExpiration] = useState(false);
  const [isEstimatedExpiration, setIsEstimatedExpiration] = useState(false);

  const estimateRequestIdRef = useRef(0);
  const hasAppliedPrefillRef = useRef(false);

  const resetForm = useCallback(() => {
    setProductId(null);
    setName("");
    setPrice("");
    setQuantity("1");
    setPurchaseDate(new Date());
    setExpirationDate(null);
    setIsPrivate(false);
    setBarcode(null);
    setIsBoughtToday(false);
    setSelectedCategory(null);
    setProductId(null);
    setIsEstimatedExpiration(false);
    setIsEstimatingExpiration(false);
  }, []);

  useFocusEffect(
    useCallback(() => {
      if (!prefill) {
        hasAppliedPrefillRef.current = false;
        resetForm();
      }

      return () => {};
    }, [prefill, resetForm]),
  );

  useEffect(() => {
    if (!prefill || categories.length === 0 || hasAppliedPrefillRef.current)
      return;

    try {
      const data = JSON.parse(prefill as string);
      setProductId(data.id_producte || null);
      setName(data.nom || "");
      setPrice(data.price || "");
      setQuantity(data.quantity || "1");
      setBarcode(data.barcode || null);
      setIsPrivate(!!data.isPrivate);

      if (data.purchaseDate) {
        setPurchaseDate(new Date(data.purchaseDate));
      } else {
        setPurchaseDate(new Date());
      }

      if (data.expirationDate) {
        setExpirationDate(new Date(data.expirationDate));
      } else {
        setExpirationDate(null);
      }

      if (typeof data.isEstimatedExpiration === "boolean") {
        setIsEstimatedExpiration(data.isEstimatedExpiration);
      } else {
        setIsEstimatedExpiration(false);
      }

      if (data.categoria) {
        const match = categories.find(
          (c) => c.value === data.categoria || c.label === data.categoria,
        );
        if (match) {
          setSelectedCategory(match);
        }
      }

      hasAppliedPrefillRef.current = true;
    } catch (e) {
      console.warn("Error al parsear el prefill", e);
    }
  }, [prefill, categories]);

  useEffect(() => {
    if (!selectedCategory?.value || !purchaseDate) return;

    estimateExpirationDate();
  }, [selectedCategory?.value, purchaseDate]);

  const estimateExpirationDate = async () => {
    if (!selectedCategory?.value || !purchaseDate) return;

    const requestId = ++estimateRequestIdRef.current;

    try {
      setIsEstimatingExpiration(true);

      const response = await inventoryService.estimateExpiration({
        categoria: selectedCategory.value,
        data_compra: purchaseDate.toISOString().split("T")[0],
      });

      if (requestId !== estimateRequestIdRef.current) return;

      if (response?.data_caducitat) {
        setExpirationDate(new Date(response.data_caducitat));
        setIsEstimatedExpiration(!!response?.data_caducitat_estimada);
      }
    } catch {
      if (requestId !== estimateRequestIdRef.current) return;
      setIsEstimatedExpiration(false);
    } finally {
      if (requestId === estimateRequestIdRef.current) {
        setIsEstimatingExpiration(false);
      }
    }
  };

  const handleManualExpirationChange = (date: Date | null) => {
    setExpirationDate(date);
    setIsEstimatedExpiration(false);
  };

  const handlePurchaseDateChange = (date: Date | null) => {
    setPurchaseDate(date);
  };

  const handleSubmit = async () => {
    if (
      !name.trim() ||
      !selectedCategory ||
      !price ||
      !quantity ||
      !purchaseDate
    ) {
      Alert.alert(
        "Camps incomplets",
        "Si us plau, omple els camps obligatoris.",
      );
      return;
    }

    const parsedPrice = parseFloat(price.replace(",", "."));
    const parsedQuantity = parseInt(quantity, 10);

    if (isNaN(parsedPrice) || parsedPrice < 0) {
      Alert.alert("Preu invàlid", "El preu ha de ser un número positiu.");
      return;
    }

    if (isNaN(parsedQuantity) || parsedQuantity <= 0 || parsedQuantity > 99) {
      Alert.alert(
        "Quantitat invàlida",
        "La quantitat ha d'estar entre 1 i 99.",
      );
      return;
    }

    setIsSubmitting(true);
    try {
      if (productId) {
        await inventoryService.updateProduct(productId, {
          nom: name.trim(),
          categoria: selectedCategory?.value,
          preu: parseFloat(price.replace(",", ".")),
          data_caducitat: expirationDate
            ? expirationDate.toISOString().split("T")[0]
            : null,
        });

        await inventoryService.updateProductOwners(productId, {
          id_producte: productId,
          owner_user_ids: isPrivate && session?.id ? [session.id] : [],
        });

        Alert.alert("¡Èxit!", "Producte actualitzat correctament.", [
          { text: "OK", onPress: () => router.replace("/(tabs)/inventory") },
        ]);
      } else {
        const commonData = {
          nom: name.trim(),
          categoria: selectedCategory?.value,
          preu: parseFloat(price.replace(",", ".")),
          quantitat: parseInt(quantity, 10),
          data_compra: purchaseDate?.toISOString().split("T")[0],
          data_caducitat: expirationDate?.toISOString().split("T")[0],
          id_propietaris_privats: isPrivate && session?.id ? [session.id] : [],
        };

        if (barcode) {
          await inventoryService.confirmBarcodeProduct({
            barcode,
            ...commonData,
          });
        } else {
          await inventoryService.createManualProduct({
            ...commonData,
            nom: commonData.nom!,
            categoria: commonData.categoria!,
            preu: commonData.preu!,
            quantitat: commonData.quantitat!,
          });
        }

        Alert.alert("¡Èxit!", "Producte guardat.", [
          { text: "OK", onPress: () => router.replace("/(tabs)/inventory") },
        ]);
      }

      resetForm();
      hasAppliedPrefillRef.current = false;
    } catch (error: any) {
      Alert.alert("Error", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const today = new Date();
  const oneWeekAgo = new Date();
  oneWeekAgo.setDate(today.getDate() - 7);

  const toggleBoughtToday = () => {
    const newValue = !isBoughtToday;
    setIsBoughtToday(newValue);
    if (newValue) {
      setPurchaseDate(new Date());
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadCategories();
    }, []),
  );

  const loadCategories = async () => {
    try {
      setIsLoadingCategories(true);
      const data = await inventoryService.getCategories();
      setCategories(data);
    } catch (error: any) {
      Alert.alert("Error", error);
      setCategories([]);
    } finally {
      setIsLoadingCategories(false);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-[#F8FAF8]">
      <SearchablePicker
        visible={isPickerVisible}
        onClose={() => setIsPickerVisible(false)}
        onSelect={setSelectedCategory}
        options={categories}
        title="Categoría del producto"
      />

      <KeyboardAwareScrollView
        contentContainerStyle={{ flexGrow: 1, paddingBottom: 40 }}
        showsVerticalScrollIndicator={false}
      >
        <View className="flex-row items-center px-4 pb-4 border-b border-gray-200">
          <TouchableOpacity
            className="w-10 h-10 rounded-xl flex items-center justify-center active:bg-gray-200"
            onPress={() => router.back()}
            disabled={isSubmitting}
          >
            <ArrowLeft color="#1F2937" size={24} />
          </TouchableOpacity>
        </View>

        <View className="px-6 space-y-6">
          <View className="items-left gap-2 my-4">
            <Text className="text-2xl font-bold text-gray-900 ">
              Afegeix el producte manualment
            </Text>
            <Text className="text-sm text-gray-500 font-medium">
              Afegeix els detalls del producte.
            </Text>
          </View>

          <View className="space-y-2">
            <Text className="font-medium text-gray-900 mb-2">
              Nom del producte <Text className="text-red-500">*</Text>
            </Text>
            <TextInput
              className="h-14 px-4 rounded-2xl bg-white border border-gray-200 text-base shadow-sm"
              value={name}
              onChangeText={setName}
              placeholder="Ej: Llet organica"
              placeholderTextColor="#9CA3AF"
              maxLength={100}
            />
          </View>

          <View className="flex-row gap-4 mt-4">
            <View className="flex-1 space-y-2">
              <Text className="font-medium text-gray-900 mb-2">
                Categoría <Text className="text-red-500">*</Text>
              </Text>
              <TouchableOpacity
                className="h-14 px-4 rounded-2xl bg-white border border-gray-200 shadow-sm flex-row items-center justify-between"
                onPress={() => setIsPickerVisible(true)}
                disabled={isLoadingCategories}
              >
                <View className="flex-row items-center flex-1 pr-2">
                  {isLoadingCategories ? (
                    <Text className="text-gray-400 text-base">
                      Carregant...
                    </Text>
                  ) : (
                    <Text
                      className={`text-base ${
                        selectedCategory ? "text-gray-900" : "text-gray-400"
                      }`}
                      numberOfLines={1}
                    >
                      {selectedCategory
                        ? selectedCategory.label
                        : "Seleccionar..."}
                    </Text>
                  )}
                </View>
                {isLoadingCategories ? (
                  <ActivityIndicator size="small" />
                ) : (
                  <ChevronDown color="#9CA3AF" size={20} />
                )}
              </TouchableOpacity>
            </View>

            <View className="flex-1 space-y-2">
              <Text className="font-medium text-gray-900 mb-2">
                Preu (€) <Text className="text-red-500">*</Text>
              </Text>
              <TextInput
                className="h-14 px-4 rounded-2xl bg-white border border-gray-200 text-base shadow-sm"
                placeholder="0.00"
                keyboardType="decimal-pad"
                value={price}
                onChangeText={setPrice}
              />
            </View>
          </View>

          <View className="flex-row gap-4 mt-4">
            <View className="flex-1 space-y-2">
              <Text className="font-medium text-gray-900 mb-2">
                Quantitat <Text className="text-red-500">*</Text>
              </Text>
              <TextInput
                className="h-14 px-4 rounded-2xl bg-white border border-gray-200 text-base shadow-sm"
                placeholder="1"
                keyboardType="number-pad"
                value={quantity}
                onChangeText={setQuantity}
                maxLength={2}
              />
            </View>

            <View className="flex-1">
              <DatePickerField
                label="Data de compra"
                value={purchaseDate}
                onChange={handlePurchaseDateChange}
                placeholder="Opcional"
                minimumDate={oneWeekAgo}
                maximumDate={today}
                disabled={isBoughtToday}
                isRequired={true}
              />
              <TouchableOpacity
                className="flex-row items-center mt-3 ml-1"
                onPress={toggleBoughtToday}
              >
                {isBoughtToday ? (
                  <CheckSquare color="#10B981" size={20} />
                ) : (
                  <Square color="#9CA3AF" size={20} />
                )}
                <Text className="ml-2 text-sm text-gray-700 font-medium">
                  Comprat avui
                </Text>
              </TouchableOpacity>
            </View>
          </View>

          <View className="flex-row gap-4 mt-4">
            <View className="flex-1">
              <DatePickerField
                label="Data de caducitat"
                value={expirationDate}
                onChange={handleManualExpirationChange}
                placeholder="Sense caducitat (Opcional)"
                minimumDate={today}
              />

              {isEstimatingExpiration ? (
                <View className="flex-row items-center mt-2 ml-1">
                  <ActivityIndicator size="small" color="#10B981" />
                  <Text className="ml-2 text-xs text-emerald-600 font-medium">
                    Estimant caducitat...
                  </Text>
                </View>
              ) : isEstimatedExpiration ? (
                <View className="flex-row items-center mt-2 ml-1">
                  <Sparkles color="#10B981" size={16} />
                  <Text className="ml-2 text-xs text-emerald-600 font-medium">
                    Data estimada automàticament
                  </Text>
                </View>
              ) : null}
            </View>
          </View>

          <View className="flex-row items-center justify-between p-4 mt-6 bg-white border border-gray-200 rounded-2xl shadow-sm">
            <View className="flex-row items-center flex-1">
              <View
                className={`p-2 rounded-xl mr-3 ${
                  isPrivate ? "bg-amber-100" : "bg-gray-100"
                }`}
              >
                {isPrivate ? (
                  <Lock color="#D97706" size={20} />
                ) : (
                  <Unlock color={isPrivate ? "#D97706" : "#9CA3AF"} size={20} />
                )}
              </View>
              <View className="flex-1 pr-4">
                <Text className="text-base font-bold text-gray-900">
                  Producte privat
                </Text>
              </View>
            </View>
            <Switch
              trackColor={{ false: "#E5E7EB", true: "#10B981" }}
              thumbColor={"#FFFFFF"}
              ios_backgroundColor="#E5E7EB"
              onValueChange={setIsPrivate}
              value={isPrivate}
            />
          </View>

          <TouchableOpacity
            className={`w-full h-14 rounded-2xl flex items-center justify-center mt-8 shadow-sm ${
              isSubmitting
                ? "bg-emerald-300"
                : "bg-emerald-500 active:bg-emerald-600"
            }`}
            onPress={handleSubmit}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text className="text-white text-lg font-bold">
                Guardar producte
              </Text>
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAwareScrollView>
    </SafeAreaView>
  );
}
