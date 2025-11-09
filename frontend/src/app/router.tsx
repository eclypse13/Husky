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
import Pedigree from "@/pages/Pedigree/Pedigree";
import President from "@/pages/President/President";
import SmartTools from "@/pages/SmartTools/SmartTools";
import Profile from "@/pages/Profile/Profile";
import PublicGallery from "@/pages/PublicGallery/PublicGallery";
import PublicWinner from "@/pages/PublicWinner/PublicWinner";


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
            { path: "pedigree", element: <Pedigree /> },
            { path: "president", element: <President /> },
            { path: "profile", element: <Profile /> },
            { path: "/smart-tools", element: <SmartTools /> },
            { path: "/public-gallery", element: <PublicGallery /> },
            { path: "/public-winner", element: <PublicWinner /> },
        ],
    },
]);
