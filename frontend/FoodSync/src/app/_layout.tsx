import { Stack } from "expo-router";
import "../../global.css";

export default function RootLayout() {
  {/*screenOptions is a prop, in this case is used to hide the default header */}
  return <Stack screenOptions={{headerShown: false}} />;
}
