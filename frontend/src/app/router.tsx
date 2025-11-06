import { createBrowserRouter } from "react-router-dom";
import RootLayout from "./layouts/RootLayout";
import Home from "@/pages/Home/Home";
import NewsList from "@/pages/News/News";
import EventsList from "@/pages/Events/Events";
import About from "@/pages/About/About";
import Breed from "@/pages/Breed/Breed";
import PuppiesList from "@/pages/Puppies/AllPuppies";
import Archive from "@/pages/Archive/Archive";
import Health from "@/pages/Health/Health"
import Rating from "@/pages/Rating/Rating";
import WinnerPage from "@/features/rating/pages/WinnerPage";
import Pedigree from "@/pages/Pedigree/Pedigree";
import GalleryPage from "@/features/gallery/pages/GalleryPage";
import ProfilePage from "@/features/profile/pages/ProfilePage";
import ToolsPage from "@/features/tools/pages/ToolsPage";
import PresidentPage from "@/features/leadership/pages/PresidentPage";
import SmartTools from "@/pages/SmartTools/SmartTools";

export const router = createBrowserRouter([
    {
        path: "/",
        element: <RootLayout />,
        children: [
            { index: true, element: <Home /> },
            { path: "news", element: <NewsList /> },
            { path: "events", element: <EventsList /> },
            { path: "about", element: <About /> },
            { path: "breed", element: <Breed /> },
            { path: "puppies", element: <PuppiesList /> },
            { path: "archive", element: <Archive /> },
            { path: "health", element: <Health /> },
            { path: "rating", element: <Rating /> },
            { path: "rating/winner/:year?", element: <WinnerPage /> },
            { path: "pedigree", element: <Pedigree /> },
            { path: "gallery", element: <GalleryPage /> },
            { path: "profile", element: <ProfilePage /> },
            { path: "tools", element: <ToolsPage /> },
            { path: "about/president", element: <PresidentPage /> },
            { path: "/smart-tools", element: <SmartTools /> },
        ],
    },
]);
