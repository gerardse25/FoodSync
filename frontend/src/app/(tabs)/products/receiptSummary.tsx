import SearchablePicker from "@/src/components/products/SearchablePicker";
import { router, useLocalSearchParams } from "expo-router";
import {
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ShoppingBag,
  Trash2,
  X,
} from "lucide-react-native";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { HomeMember, homeService } from "../../../services/homeService";
import { inventoryService } from "../../../services/inventoryService";

export default function ReceiptSummaryScreen() {
  const { productsData } = useLocalSearchParams();

  const [products, setProducts] = useState<any[]>(
    productsData ? JSON.parse(productsData as string) : [],
  );
  const [isSaving, setIsSaving] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [members, setMembers] = useState<HomeMember[]>([]);
  const [categories, setCategories] = useState<
    { label: string; value: string }[]
  >([]);
  const [isLoadingCategories, setIsLoadingCategories] = useState(true);
  const [isPickerVisible, setIsPickerVisible] = useState(false);

  useEffect(() => {
    if (productsData) {
      setProducts(JSON.parse(productsData as string));
      setEditingIndex(null);
    }
  }, [productsData]);

  useEffect(() => {
    const fetchMembers = async () => {
      try {
        const homeData = await homeService.getHome();
        const homeMembers =
          homeData.membres ||
          homeData.members ||
          homeData.home?.membres ||
          homeData.llar?.membres ||
          [];
        setMembers(homeMembers);
      } catch (error) {
        console.error("No s'han pogut carregar els membres de la llar", error);
      }
    };
    const loadCategories = async () => {
      try {
        setIsLoadingCategories(true);
        const data = await inventoryService.getCategories();
        setCategories(data);
      } catch (error) {
        console.error("Error al carregar categories", error);
      } finally {
        setIsLoadingCategories(false);
      }
    };

    fetchMembers();
    loadCategories();
  }, []);

  const [editForm, setEditForm] = useState({
    nom: "",
    preu: "",
    quantitat: "1",
    categoria: "",
    categoria_label: "",
    id_propietaris_privats: [] as string[],
  });

  const startEditing = (index: number) => {
    const prod = products[index];
    setEditForm({
      nom: prod.nom || "",
      preu: prod.preu?.toString() || "0",
      quantitat: prod.quantitat?.toString() || "1",
      categoria: prod.categoria || "", 
      categoria_label: prod.categoria_label || "Sense categoria",
      id_propietaris_privats: prod.id_propietaris_privats || [],
    });
    setEditingIndex(index);
  };

  const saveEdit = () => {
    if (editingIndex !== null) {
      const updatedProducts = [...products];
      updatedProducts[editingIndex] = {
        ...updatedProducts[editingIndex],
        nom: editForm.nom,
        preu: parseFloat(editForm.preu.replace(",", ".")) || 0,
        quantitat: parseInt(editForm.quantitat, 10) || 1,
        categoria: editForm.categoria,
        categoria_label: editForm.categoria_label,
        id_propietaris_privats: editForm.id_propietaris_privats,
      };
      setProducts(updatedProducts);
      setEditingIndex(null);
    }
  };

  const handleDeleteProduct = (indexToDelete: number) => {
    const productToDelete = products[indexToDelete];

    Alert.alert(
      "Eliminar producte",
      `Vols eliminar "${productToDelete?.nom || "aquest producte"}" del resum del tiquet?`,
      [
        {
          text: "Cancel·lar",
          style: "cancel",
        },
        {
          text: "Eliminar",
          style: "destructive",
          onPress: () => {
            setProducts((prev) =>
              prev.filter((_, index) => index !== indexToDelete),
            );

            if (editingIndex === indexToDelete) {
              setEditingIndex(null);
            } else if (editingIndex !== null && indexToDelete < editingIndex) {
              setEditingIndex(editingIndex - 1);
            }
          },
        },
      ],
    );
  };

  const handleSaveAll = async () => {
    if (products.length === 0) {
      Alert.alert(
        "Sense productes",
        "No hi ha productes per guardar. Afegeix-ne o torna enrere.",
      );
      return;
    }

    setIsSaving(true);
    try {
      const formattedProducts = products.map((prod: any) => {
        let parsedPreu = null;
        if (prod.preu !== undefined && prod.preu !== null && prod.preu !== "") {
          const preuNum = parseFloat(String(prod.preu).replace(",", "."));
          if (!isNaN(preuNum)) {
            parsedPreu = preuNum;
          }
        }

        let parsedQuantitat = 1;
        if (prod.quantitat !== undefined && prod.quantitat !== null) {
          const qNum = parseInt(String(prod.quantitat), 10);
          if (!isNaN(qNum) && qNum > 0) {
            parsedQuantitat = qNum;
          }
        }

        let safeNutriscore = null;
        if (typeof prod.nutriscore === "string") {
          const cleanNutriscore = prod.nutriscore.trim().toUpperCase();
          if (["A", "B", "C", "D", "E"].includes(cleanNutriscore)) {
            safeNutriscore = cleanNutriscore;
          }
        }

        return {
          nom: String(prod.nom || "Producte sense nom"),
          categoria: prod.categoria || "OTHER",
          preu: parsedPreu,
          quantitat: parsedQuantitat,
          data_compra:
            prod.data_compra || new Date().toISOString().split("T")[0],
          data_caducitat: prod.data_caducitat
            ? String(prod.data_caducitat)
            : null,
          id_propietaris_privats: Array.isArray(prod.id_propietaris_privats)
            ? prod.id_propietaris_privats
            : [],
          data_caducitat_estimada: Boolean(prod.data_caducitat_estimada),

          marca: prod.marca || null,
          imatge_url: prod.imatge_url || null,
          nutriscore: safeNutriscore,
          quantitat_envas: prod.quantitat_envas || null,
          ingredients_text: prod.ingredients_text || null,
          allergens_text: prod.allergens_text || null,
          nutriments_per_100g: prod.nutriments_per_100g || null,

          nutrient_levels: prod.nutrient_levels || null,
          nutriments_100g: prod.nutriments_100g || null,
        };
      });
      console.log(
        "DATOS ENVIADOS AL BACKEND:",
        JSON.stringify(formattedProducts[0], null, 2),
      );
      await inventoryService.confirmReceiptTicket(formattedProducts);

      Alert.alert(
        "Tiquet guardat!",
        "Tots els productes s'han afegit a l'inventari correctament.",
        [
          {
            text: "D'acord",
            onPress: () => router.replace("/(tabs)/inventory"),
          },
        ],
      );
    } catch (error: any) {
      let errorMessage = "Hi ha hagut un problema guardant els productes.";

      if (typeof error === "string") {
        errorMessage = error;
      } else if (Array.isArray(error)) {
        errorMessage = error
          .map((e: any) => `Error a ${e.loc?.join(" -> ")}: ${e.msg}`)
          .join("\n\n");
      } else if (error && typeof error === "object") {
        errorMessage = JSON.stringify(error, null, 2);
      }

      console.error("Error complet:", error);
      Alert.alert("Error de validació (422)", errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <SafeAreaView edges={["top"]} className="flex-1 bg-[#F8FAF8]">
      <SearchablePicker
        visible={isPickerVisible}
        onClose={() => setIsPickerVisible(false)}
        onSelect={(cat) => {
          setEditForm((prev) => ({
            ...prev,
            categoria: cat.value,
            categoria_label: cat.label,
          }));
          setIsPickerVisible(false);
        }}
        options={categories}
        title="Categoria del producte"
      />
      <View className="px-4 py-4 flex-row items-center border-b border-gray-100 bg-white shadow-sm z-10">
        <TouchableOpacity
          onPress={() => router.back()}
          className="p-2 -ml-2"
          disabled={isSaving}
        >
          <ArrowLeft color="#1F2937" size={24} />
        </TouchableOpacity>
        <Text className="text-xl font-bold text-gray-900 ml-2">
          Resum del Tiquet
        </Text>
      </View>

      <ScrollView
        className="flex-1 px-6 pt-6 mb-8"
        contentContainerStyle={{ paddingBottom: 100 }}
      >
        <Text className="text-gray-500 mb-6">
          Hem trobat {products.length} productes. Revisa&apos;ls, edita&apos;ls
          si cal i elimina els que no vulguis guardar.
        </Text>

        <View className="space-y-3">
          {products.map((prod, index) => (
            <View
              key={index}
              className="bg-white p-4 rounded-2xl border border-gray-100 flex-row items-center justify-between shadow-sm mb-4"
            >
              <TouchableOpacity
                className="flex-1 flex-row items-center"
                onPress={() => startEditing(index)}
                activeOpacity={0.8}
              >
                <View className="w-10 h-10 bg-emerald-50 rounded-full items-center justify-center mr-3">
                  {prod.imatge_url ? (
                    <Image
                      source={{ uri: prod.imatge_url }}
                      className="w-full h-full rounded-full"
                    />
                  ) : (
                    <ShoppingBag color="#10B981" size={20} />
                  )}
                </View>

                <View className="flex-1 pr-4">
                  <Text
                    className="text-base font-bold text-gray-900"
                    numberOfLines={1}
                  >
                    {prod.nom}
                  </Text>
                  <Text className="text-sm text-emerald-600 font-medium">
                    {prod.categoria_label || "Sense categoria"}
                  </Text>
                </View>
              </TouchableOpacity>

              <View className="items-end mr-3">
                <Text className="font-bold text-gray-900">{prod.preu} €</Text>
                <Text className="text-xs text-gray-500">x{prod.quantitat}</Text>
              </View>

              <TouchableOpacity
                className="w-10 h-10 rounded-full bg-red-50 items-center justify-center border border-red-100"
                onPress={() => handleDeleteProduct(index)}
                disabled={isSaving}
              >
                <Trash2 color="#EF4444" size={18} />
              </TouchableOpacity>
            </View>
          ))}
        </View>

        {products.length === 0 ? (
          <View className="bg-white rounded-2xl border border-dashed border-gray-300 p-6 items-center mt-2">
            <Text className="text-base font-semibold text-gray-700">
              No hi ha productes al resum
            </Text>
            <Text className="text-sm text-gray-500 text-center mt-2">
              Torna enrere per tornar a escanejar o afegeix només els que
              t&apos;interessin.
            </Text>
          </View>
        ) : null}
      </ScrollView>

      <View className="absolute bottom-0 w-full bg-white border-t border-gray-100 px-6 pt-4 shadow-lg pb-12">
        <TouchableOpacity
          className={`w-full h-14 rounded-2xl flex-row items-center justify-center ${
            products.length === 0 || isSaving
              ? "bg-emerald-300"
              : "bg-emerald-500 active:bg-emerald-600"
          }`}
          onPress={handleSaveAll}
          disabled={isSaving || products.length === 0}
        >
          {isSaving ? (
            <ActivityIndicator color="white" />
          ) : (
            <>
              <CheckCircle2 color="white" size={20} />
              <Text className="text-white font-bold text-lg ml-2">
                Guardar tots els productes
              </Text>
            </>
          )}
        </TouchableOpacity>
      </View>

      {editingIndex !== null && (
        <View className="absolute inset-0 bg-black/60 justify-end z-50">
          <TouchableOpacity
            className="flex-1"
            onPress={() => setEditingIndex(null)}
          />
          <KeyboardAvoidingView
            behavior={Platform.OS === "ios" ? "padding" : undefined}
          >
            <View className="bg-white rounded-t-3xl px-6 pt-6 pb-12">
              <View className="flex-row justify-between items-center mb-6">
                <Text className="text-xl font-bold text-gray-900">
                  Editar Producte
                </Text>
                <TouchableOpacity
                  onPress={() => setEditingIndex(null)}
                  className="p-2 bg-gray-100 rounded-full"
                >
                  <X color="#4B5563" size={20} />
                </TouchableOpacity>
              </View>

              <View className="space-y-4">
                <View>
                  <Text className="text-sm font-bold text-gray-700 mb-2">
                    Nom del producte
                  </Text>
                  <TextInput
                    className="h-14 bg-gray-50 border border-gray-200 rounded-xl px-4 text-base"
                    value={editForm.nom}
                    onChangeText={(t) => setEditForm({ ...editForm, nom: t })}
                  />
                </View>
                <View className="mt-2">
                  <Text className="text-sm font-bold text-gray-700 mb-2">
                    Categoria
                  </Text>
                  <TouchableOpacity
                    className="h-14 bg-gray-50 border border-gray-200 rounded-xl px-4 flex-row items-center justify-between"
                    onPress={() => setIsPickerVisible(true)}
                    disabled={isLoadingCategories}
                  >
                    <Text
                      className={`text-base ${editForm.categoria ? "text-gray-900" : "text-gray-400"}`}
                    >
                      {isLoadingCategories
                        ? "Carregant..."
                        : editForm.categoria_label ||
                          "Selecciona una categoria"}
                    </Text>
                    <ChevronDown color="#9CA3AF" size={20} />
                  </TouchableOpacity>
                </View>
                <View className="flex-row gap-4">
                  <View className="flex-1">
                    <Text className="text-sm font-bold text-gray-700 mb-2">
                      Preu (€)
                    </Text>
                    <TextInput
                      className="h-14 bg-gray-50 border border-gray-200 rounded-xl px-4 text-base"
                      keyboardType="decimal-pad"
                      value={editForm.preu}
                      onChangeText={(t) =>
                        setEditForm({ ...editForm, preu: t })
                      }
                    />
                  </View>
                  <View className="flex-1">
                    <Text className="text-sm font-bold text-gray-700 mb-2">
                      Quantitat
                    </Text>
                    <TextInput
                      className="h-14 bg-gray-50 border border-gray-200 rounded-xl px-4 text-base"
                      keyboardType="number-pad"
                      value={editForm.quantitat}
                      onChangeText={(t) =>
                        setEditForm({ ...editForm, quantitat: t })
                      }
                    />
                  </View>
                </View>

                <View className="mt-2">
                  <Text className="text-sm font-bold text-gray-700 mb-1">
                    Assignar un propietari privat
                  </Text>
                  <Text className="text-xs text-gray-500 mb-3">
                    Si no selecciones ningú, el producte serà per a tota la
                    llar.
                  </Text>

                  {members.length > 0 ? (
                    <View className="flex-row flex-wrap gap-2">
                      {members.map((member: any, index: number) => {
                        const memberId = member.user_id;
                        const memberName = member.username;
                        const isSelected =
                          editForm.id_propietaris_privats.includes(memberId);

                        return (
                          <TouchableOpacity
                            key={`member-${memberId}-${index}`}
                            onPress={() => {
                              setEditForm((prev) => {
                                const current = prev.id_propietaris_privats;
                                if (current.includes(memberId)) {
                                  return {
                                    ...prev,
                                    id_propietaris_privats: [],
                                  };
                                }
                                return {
                                  ...prev,
                                  id_propietaris_privats: [memberId],
                                };
                              });
                            }}
                            className={`px-4 py-2 rounded-xl border ${
                              isSelected
                                ? "bg-emerald-500 border-emerald-500"
                                : "bg-white border-gray-300"
                            }`}
                          >
                            <Text
                              className={
                                isSelected
                                  ? "text-white font-bold"
                                  : "text-gray-700 font-medium"
                              }
                            >
                              {memberName}
                            </Text>
                          </TouchableOpacity>
                        );
                      })}
                    </View>
                  ) : (
                    <Text className="text-sm text-gray-400 italic">
                      Carregant membres...
                    </Text>
                  )}
                </View>

                <TouchableOpacity
                  className="w-full h-14 bg-gray-900 rounded-xl items-center justify-center mt-4"
                  onPress={saveEdit}
                >
                  <Text className="text-white font-bold text-lg">
                    Confirmar canvis
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          </KeyboardAvoidingView>
        </View>
      )}
    </SafeAreaView>
  );
}
