from boto.s3.connection import S3Connection
from boto.s3.key import Key

from django.conf import settings


MIME_TYPE_BY_EXTENSION = {'png': 'image/png', 'jpg': 'image/jpeg', 'gif': 'image/gif'}


def get_thumbnail_sizing_params(original_size, target_size):
	"""
		Given the dimensions of a source image, return a (crop_params, resize_params) tuple that
		specifies how the image should be cropped and resized to generate a thumbnail to fit
		within target_size.
		crop_params = (left, upper, right, lower) or None for no cropping
		resize_params = (width, height) or None for no resizing

		The rules applied are:
		* all resize operations preserve aspect ratio
		* an image smaller than target_size is left unchanged
		* an image with an aspect ratio more than twice as wide as target_size is resized to half
			the target height (or left at original size if it's already this short or shorter), and
			cropped centrally to fit target width.
		* an image with an aspect ratio between 1 and 2 times as wide as target_size is resized to
			fit target width
		* an image with an aspect ratio between 1 and 3 times as tall as target_size is resized to
			fit target height
		* an image with an aspect ratio more than three times as tall as target_size is resized to
			one third of the target width (or left at original size if it's already this narrow or
			narrower), and cropped to the top to fit target height.
	"""
	orig_width, orig_height = original_size
	target_width, target_height = target_size

	if orig_width <= target_width and orig_height <= target_height:
		# image is smaller than target size - do not crop or resize
		return (None, None)

	orig_aspect_ratio = float(orig_width) / orig_height
	target_aspect_ratio = float(target_width) / target_height

	if orig_aspect_ratio > 2 * target_aspect_ratio:
		# image with an aspect ratio more than twice as wide as target_size
		final_width = target_width
		final_height = min(orig_height, target_height / 2)
		scale_factor = float(final_height) / orig_height

		# scale up final_width to find out what we should crop to
		crop_width = final_width / scale_factor
		crop_margin = int((orig_width - crop_width) / 2)
		crop_params = (crop_margin, 0, crop_margin + int(crop_width), orig_height)
		if final_height == orig_height:
			resize_params = None
		else:
			resize_params = (final_width, final_height)
		return (crop_params, resize_params)
	elif orig_aspect_ratio >= target_aspect_ratio:
		# image with aspect ratio equal or wider to target_size
		final_width = target_width
		scale_factor = float(final_width) / orig_width
		final_height = int(orig_height * scale_factor)
		resize_params = (final_width, final_height)
		return (None, resize_params)
	elif orig_aspect_ratio >= target_aspect_ratio / 3:
		# image with taller aspect ratio than target_size, but not more than 3 times taller
		# (so no need to crop)
		final_height = target_height
		scale_factor = float(final_height) / orig_height
		final_width = int(orig_width * scale_factor)
		resize_params = (final_width, final_height)
		return (None, resize_params)
	else:
		# image with an aspect ratio more than 3 times taller than target_size
		final_height = target_height
		final_width = min(orig_width, target_width / 3)
		scale_factor = float(final_width) / orig_width

		# scale up final_height to find out what we should crop to:
		crop_height = final_height / scale_factor
		crop_params = (0, 0, orig_width, int(crop_height))
		if final_width == orig_width:
			resize_params = None
		else:
			resize_params = (final_width, final_height)
		return (crop_params, resize_params)


def upload_to_s3(fp, key_name, extension, reduced_redundancy=False):
	"""
		Upload the contents of file handle 'fp' to the S3 bucket specified by AWS_STORAGE_BUCKET_NAME,
		under the given filename. Return the public URL.
	"""

	# connect to S3 and send the file contents
	conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
	bucket = conn.get_bucket(settings.AWS_STORAGE_BUCKET_NAME)
	k = Key(bucket)
	k.key = key_name
	k.content_type = MIME_TYPE_BY_EXTENSION.get(extension, 'application/octet-stream')
	# print "uploading: %s" % key_name
	k.set_contents_from_file(fp, reduced_redundancy=reduced_redundancy, rewind=True)
	k.set_acl('public-read')

	# construct the resulting URL, which depends on whether we're using a CNAME alias
	# on our bucket
	if settings.AWS_BOTO_CALLING_FORMAT == 'VHostCallingFormat':
		return "http://%s/%s" % (settings.AWS_STORAGE_BUCKET_NAME, key_name)
	else:
		return "http://%s.s3.amazonaws.com/%s" % (settings.AWS_STORAGE_BUCKET_NAME, key_name)