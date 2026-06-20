import DEFAULT_DOG_IMG from "@/assets/no-image-dog.png";

const PLACEHOLDER_URLS = ["https://zooportal.pro/images/logo1.png"];

export function dogPhoto(
    dog_photo: string | null | undefined,
    photoUrl: string | null | undefined = null,
): string {
    const url = dog_photo || photoUrl;
    return url && !PLACEHOLDER_URLS.includes(url) ? url : DEFAULT_DOG_IMG;
}

export {DEFAULT_DOG_IMG, PLACEHOLDER_URLS};