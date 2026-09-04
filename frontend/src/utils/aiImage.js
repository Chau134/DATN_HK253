import { aiApi } from '../api/aiApi';

const MAX_IMAGE_SIDE = 1280;
const IMAGE_JPEG_QUALITY = 0.86;

export function cropBoxOf(image) {
    return image?.cropBox || undefined;
}

export async function imageWithDetections(image) {
    const data = await aiApi.detectImage({ image: image.payload });
    const detections = data.detections || [];
    const yoloCropBox = detections[0]?.bbox || null;
    const cropBox = yoloCropBox || image.cropBox || null;
    const warnings = Array.from(new Set([...(image.warnings || []), ...(data.warnings || [])]));

    return {
        ...image,
        width: data.image_width || image.width,
        height: data.image_height || image.height,
        detections,
        warnings,
        cropBox,
        cropSource: yoloCropBox ? 'yolo' : image.cropSource,
    };
}

export async function imagePayloadFromFile(file) {
    if (!file.type?.startsWith('image/')) {
        throw new Error('Vui lòng chọn một file ảnh.');
    }

    const dataUrl = await readFileAsDataUrl(file);
    const compressed = await compressImageDataUrl(dataUrl);
    const [, compressedBase64 = ''] = compressed.dataUrl.split(',');
    return {
        preview: compressed.dataUrl,
        filename: file.name,
        width: compressed.width,
        height: compressed.height,
        detections: [],
        warnings: compressed.wasCompressed ? ['Ảnh đã được nén để gửi lên AI nhanh hơn.'] : [],
        cropBox: null,
        cropSource: 'full',
        payload: {
            content_type: 'image/jpeg',
            data_base64: compressedBase64,
            filename: file.name,
        },
    };
}

export function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ''));
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

export function loadImageElement(src) {
    return new Promise((resolve, reject) => {
        const img = new window.Image();
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = src;
    });
}

export async function compressImageDataUrl(src) {
    const img = await loadImageElement(src);
    const sourceWidth = img.naturalWidth || 1;
    const sourceHeight = img.naturalHeight || 1;
    const scale = Math.min(1, MAX_IMAGE_SIDE / Math.max(sourceWidth, sourceHeight));
    const width = Math.max(1, Math.round(sourceWidth * scale));
    const height = Math.max(1, Math.round(sourceHeight * scale));

    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext('2d');
    context.fillStyle = '#ffffff';
    context.fillRect(0, 0, width, height);
    context.drawImage(img, 0, 0, width, height);

    const dataUrl = canvas.toDataURL('image/jpeg', IMAGE_JPEG_QUALITY);
    return {
        dataUrl,
        width,
        height,
        wasCompressed: width !== sourceWidth || height !== sourceHeight || dataUrl.length < src.length,
    };
}
