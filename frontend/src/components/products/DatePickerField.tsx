import { Calendar } from "lucide-react-native";
import React, { useState } from "react";
import { Text, TouchableOpacity, View } from "react-native";
import DateTimePickerModal from "react-native-modal-datetime-picker";

interface DatePickerFieldProps {
  label: string;
  value: Date | null;
  onChange: (date: Date) => void;
  placeholder?: string;
  minimumDate?: Date;
  maximumDate?: Date;
  disabled?: boolean;
  isRequired?: boolean;
}

export default function DatePickerField({
  label,
  value,
  onChange,
  placeholder = "Seleccionar data",
  minimumDate,
  maximumDate,
  disabled = false,
  isRequired = false,
}: DatePickerFieldProps) {
  const [isDatePickerVisible, setDatePickerVisibility] = useState(false);

  const handleConfirm = (date: Date) => {
    onChange(date);
    setDatePickerVisibility(false);
  };

  const displayDate = value ? value.toISOString().split("T")[0] : placeholder;

  return (
    <View className="flex-1">
      <Text className="font-medium text-gray-900 mb-2">
        {label}
        {isRequired && <Text className="text-red-500"> *</Text>}
      </Text>

      <TouchableOpacity
        className={`flex-row items-center h-14 px-4 rounded-2xl border shadow-sm ${
          disabled ? "bg-gray-100 border-gray-100" : "bg-white border-gray-200"
        }`}
        onPress={() => {
          if (!disabled) setDatePickerVisibility(true);
        }}
        disabled={disabled}
      >
        <Calendar color={disabled ? "#D1D5DB" : "#9CA3AF"} size={18} />
        <Text
          className={`ml-2 flex-1 text-base ${
            value && !disabled ? "text-gray-900" : "text-gray-400"
          }`}
        >
          {displayDate}
        </Text>
      </TouchableOpacity>

      <DateTimePickerModal
        isVisible={isDatePickerVisible}
        mode="date"
        display="inline"
        onConfirm={handleConfirm}
        onCancel={() => setDatePickerVisibility(false)}
        date={value || new Date()}
        minimumDate={minimumDate}
        maximumDate={maximumDate}
        confirmTextIOS="Confirmar"
        cancelTextIOS="Cancelar"
        pickerContainerStyleIOS={{
          justifyContent: "center",
          alignItems: "center",
        }}
      />
    </View>
  );
}
