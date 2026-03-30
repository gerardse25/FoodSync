import React from 'react';
import { View, Text } from 'react-native';


// Definimos los tipos de las props con TypeScript
interface FeatureItemProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

export function FeatureItem({ icon, title, description }: FeatureItemProps) {
  return (
    <View className="flex-row gap-4 items-center">
      <View className="flex-shrink-0 w-16 h-16 bg-emerald-50 rounded-xl flex items-center justify-center">
        {icon}
      </View>
      <View className="flex-1 place-content-between">
        <Text className="font-semibold text-gray-900 mb-1 text-lg">{title}</Text>
        <Text className="text-base text-gray-500 leading-5">{description}</Text>
      </View>
    </View>
  );
}